import re

from dateutil.relativedelta import relativedelta
from odoo import api, models

from .res_company_jurisdiction_padron import PARP_CONTRIBUTOR_MULTILATERAL

# Única jurisdicción cuyo padrón informa el régimen del contribuyente y, con eso, la base
# de la retención. En el resto, iibb_total es una base que se configura como cualquier otra
# (ej. Neuquén, comprobantes sin IVA discriminado) y filtrar por ella cambiaría la base en
# silencio y duplicaría impuestos.
SANTA_FE_JURISDICTION_CODE = "921"

# Bases de IIBB: el cálculo de la retención sólo retiene sobre el total con 'iibb_total'
# (ver l10n_ar.payment.withholding._compute_base_amount), y la base vacía es base neta.
IIBB_TAX_TYPES = ("iibb_untaxed", "iibb_total")

# Sufijo para distinguir en la UI la variante que retiene sobre el total (Convenio
# Multilateral) de la que retiene sobre la base neta, cuando comparten alícuota.
IIBB_TOTAL_TAX_NAME_SUFFIX = "CM"

# Clave con la que _get_tax_from_ws le pasa la base pedida a _ensure_tax, al que el flujo
# nativo llama sin ese dato.
PADRON_TAX_TYPE_CONTEXT_KEY = "l10n_ar_padron_tax_type"


class AccountFiscalPositionL10nArTax(models.Model):
    _inherit = "account.fiscal.position.l10n_ar_tax"

    def _padron_defines_base(self):
        """True si la línea retiene sobre una jurisdicción cuyo padrón define la base."""
        self.ensure_one()
        return (
            self.tax_type == "withholding"
            and self.default_tax_id.l10n_ar_state_id.jurisdiction_code == SANTA_FE_JURISDICTION_CODE
        )

    def _get_parp_tax_type(self, contributor_type):
        """Traduce el tipo de contribuyente del PARP ('C' / 'D') a la base de la retención.

        Sólo el Convenio Multilateral desvía la base. Al local le corresponde la base neta,
        pero no la pedimos: esa es ya la base de las retenciones de Santa Fe, y forzarla
        pisaría una base total configurada a propósito, que es una decisión sobre los
        comprobantes del proveedor (IVA no discriminado) y no sobre el régimen.

        Sólo aplica a retenciones: en percepciones la base no cambia por el régimen de
        convenio (lo que define si se detrae el IVA es la condición del adquirente frente
        al IVA, art. 385 inc. j) pto. 2), y el 50% del art. 387 es otro mecanismo.
        """
        self.ensure_one()
        if self.tax_type != "withholding":
            return False
        return "iibb_total" if contributor_type == PARP_CONTRIBUTOR_MULTILATERAL else False

    def _get_padron_tax_type(self, partner, date):
        """Base que pide el padrón para este contacto, o False si no pide ninguna (no es una
        jurisdicción que la defina, no hay padrón cargado, o el CUIT no figura y se le aplica
        la alícuota de castigo con la base del impuesto configurado)."""
        self.ensure_one()
        if not self._padron_defines_base():
            return False
        padron_file = self._search_padron_file(self.default_tax_id.l10n_ar_state_id, date)
        if not padron_file:
            return False
        return self._get_parp_tax_type(padron_file._get_parp_contributor_type(partner.vat))

    def _get_configured_tax_type(self):
        """Base del impuesto configurado en la línea, que es la que vale cuando el padrón no
        pide una. La base vacía cuenta como base neta: el campo no es obligatorio y en las
        bases instaladas suele estar así."""
        self.ensure_one()
        base = self.default_tax_id.l10n_ar_tax_type
        return base if base in IIBB_TAX_TYPES else "iibb_untaxed"

    def _get_tax_type_domain(self, l10n_ar_tax_type):
        """Dominio de la base para buscar el impuesto. No siempre es una igualdad: los
        impuestos con la base vacía son de base neta, y dejarlos afuera haría que se cree un
        duplicado con el mismo nombre en vez de reusarlos."""
        if l10n_ar_tax_type == "iibb_untaxed":
            return [("l10n_ar_tax_type", "in", ["iibb_untaxed", False])]
        return [("l10n_ar_tax_type", "=", l10n_ar_tax_type)]

    @api.depends("fiscal_position_id", "tax_type")
    def _compute_tax_template_domain(self):
        """Saca de la selección de impuesto por defecto la variante de Convenio Multilateral,
        que la crea el padrón (ver _ensure_tax): elegirla a mano haría que el flujo del padrón
        heredara esa base para cualquier contribuyente, incluido el local.

        La reconocemos por el sufijo que le pone _ensure_tax sobre una base total, y no por
        (jurisdicción, base): un impuesto sobre el total configurado a propósito (IVA no
        discriminado) es legítimo en cualquier jurisdicción y se sigue pudiendo elegir.
        """
        super()._compute_tax_template_domain()
        for rec in self:
            rec.tax_template_domain = rec._get_tax_domain(filter_tax_group=False) + [
                "!",
                "&",
                ("l10n_ar_tax_type", "=", "iibb_total"),
                ("name", "=like", f"% {IIBB_TOTAL_TAX_NAME_SUFFIX}"),
            ]

    def _get_tax_from_ws(self, partner, date):
        """Resuelve la base antes de que el flujo nativo busque el impuesto y se la pasa por
        contexto, porque el nativo llama a _ensure_tax sólo con la alícuota."""
        self.ensure_one()
        # Misma fecha con la que el nativo busca el padrón (primer día del mes del pago).
        tax_type = self._get_padron_tax_type(partner, date + relativedelta(day=1))
        rec = self.with_context(**{PADRON_TAX_TYPE_CONTEXT_KEY: tax_type}) if tax_type else self
        return super(AccountFiscalPositionL10nArTax, rec)._get_tax_from_ws(partner, date)

    def _ensure_tax(self, rate, l10n_ar_tax_type=None):
        """Suma la base a la búsqueda del impuesto de la alícuota dada: un 0,6% sobre base
        neta y un 0,6% sobre el total son impuestos distintos y sin esto caen sobre el mismo
        account.tax. Cuando sólo existe el de base neta, la variante de Convenio Multilateral
        se crea copiándolo, con el sufijo "CM" en el nombre.

        :param l10n_ar_tax_type: base pedida por el padrón. Sin pedido vale la del impuesto
            configurado en la línea (ver _get_configured_tax_type).
        """
        self.ensure_one()
        if not self._padron_defines_base():
            return super()._ensure_tax(rate)
        base = l10n_ar_tax_type or self.env.context.get(PADRON_TAX_TYPE_CONTEXT_KEY)
        base = base or self._get_configured_tax_type()
        domain = self._get_tax_domain() + self._get_tax_type_domain(base) + [("amount", "=", rate)]
        tax = self.env["account.tax"].with_context(active_test=False).search(domain, limit=1)
        if tax:
            if not tax.active:
                tax.active = True
            return tax
        # Mismo nombre que arma el nativo, porque el impuesto se copia igual del configurado.
        template_tax = self.default_tax_id
        if "%" not in template_tax.name:
            name = f"{template_tax.name} {rate}%"
        else:
            name = re.sub(r"\b\d+(\.\d+)?\s*%", f"{rate}%", template_tax.name)
        if base == "iibb_total" and template_tax.l10n_ar_tax_type != "iibb_total":
            # El sufijo cuelga de la base que se escribe, heredada o pedida: sin él quedaría
            # con el mismo nombre que la de base neta, y el duplicado es silencioso porque
            # las retenciones son type_tax_use='none' y _constrains_name no las alcanza. Es
            # además lo que la distingue de una base total configurada a propósito en el
            # selector de impuesto por defecto (ver _compute_tax_template_domain).
            name = f"{name} {IIBB_TOTAL_TAX_NAME_SUFFIX}"
        return template_tax.copy(
            default={
                # dejamos sequencia mas baja para que siempre el que se duplica sea el que esta arriba
                "sequence": 10,
                "amount": rate,
                "active": True,
                "l10n_ar_tax_type": base,
                "name": name,
            }
        )
