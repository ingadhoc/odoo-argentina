##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.osv import expression

# Los campos donde vive la autorización de AFIP, por variante de localización. Ninguna
# es dependencia de este módulo y nada impide que estén las dos instaladas a la vez.
AFIP_AUTH_FIELDS = (
    # Enterprise (l10n_ar_edi)
    ("l10n_ar_afip_auth_mode", "l10n_ar_afip_auth_code"),
    # Community (l10n_ar_afipws_fe, de odoo-argentina-ce)
    ("afip_auth_mode", "afip_auth_code"),
)

# Modos que significan "AFIP ya autorizó este comprobante". Mismo criterio que usa
# l10n_ar_afipws_fe en _compute_qr_code: CAE y CAEA sí, CAI no (el CAI lo otorga AFIP
# a la imprenta del talonario preimpreso, el comprobante nunca se envió al webservice).
AFIP_AUTHORIZED_MODES = ("CAE", "CAEA")


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("reversed_entry_id")
    def _compute_invoice_currency_rate(self):
        super()._compute_invoice_currency_rate()
        ar_reversed_other_currency = self.filtered(
            lambda x: (
                x.is_invoice()
                and x.reversed_entry_id
                and x.company_id.country_id == self.env.ref("base.ar")
                and x.currency_id != x.company_id.currency_id
                and x.reversed_entry_id.currency_id == x.currency_id
            )
        )
        for rec in ar_reversed_other_currency:
            rec.invoice_currency_rate = rec.reversed_entry_id.invoice_currency_rate

    def _get_name_invoice_report(self):
        """Use always argentinian like report (regardless use documents)"""
        self.ensure_one()
        if self.company_id.country_id.code == "AR":
            return "l10n_ar.report_invoice_document"
        return super()._get_name_invoice_report()

    def _l10n_ar_include_vat(self):
        self.ensure_one()
        if not self.l10n_latam_use_documents:
            discriminate_taxes = self.journal_id.discriminate_taxes
            if discriminate_taxes == "yes":
                return False
            elif discriminate_taxes == "no":
                return True
            else:
                return not (
                    self.company_id.l10n_ar_company_requires_vat
                    and self.partner_id.l10n_ar_afip_responsibility_type_id.code in ["1"]
                    or False
                )
        return self.l10n_latam_document_type_id.l10n_ar_letter in ["B", "C", "X", "R"]

    @api.model
    def _l10n_ar_get_document_number_parts(self, document_number, document_type_code):
        # eliminamos todo lo que viene después '(' que es un sufijo que odoo agrega y que nosotros agregamos para
        # forzar unicidad con cambios de approach al ir migrando de versiones
        document_number = document_number.split("(")[0]
        return super()._l10n_ar_get_document_number_parts(document_number, document_type_code)

    def _l10n_ar_afip_authorized(self):
        """Indica si AFIP ya autorizó el comprobante (``AFIP_AUTHORIZED_MODES``).

        Los campos de autorización los declaran módulos distintos según la variante de
        localización instalada (ver ``AFIP_AUTH_FIELDS``) y este módulo no depende de
        ninguno de los dos, así que leer un nombre que no está en el registry levanta
        ``AttributeError``. Miramos todos los pares que existan, no el primero: nada
        impide tener ``l10n_ar_edi`` y ``l10n_ar_afipws_fe`` instalados a la vez, y en
        ese caso alcanza con que CUALQUIERA de los dos tenga la autorización cargada.

        Devuelve ``False`` cuando no hay ningún par (por ejemplo con ``l10n_ar`` solo,
        sin facturación electrónica).
        """
        self.ensure_one()
        return any(
            self[mode_field] in AFIP_AUTHORIZED_MODES and self[code_field]
            for mode_field, code_field in AFIP_AUTH_FIELDS
            if mode_field in self._fields and code_field in self._fields
        )

    def button_cancel(self):
        """
        Evitamos que se pueda cancelar una factura que ya fue previamente confirmada y enviada a AFIP.
        Este caso se da cuando dos usuarios están a la vez editando la misma factura, uno confirma
        y el otro, sin refrescar, cancela.
        """
        if posted_in_afip := self.filtered(
            lambda x: (x.state == "posted" and x.invoice_filter_type_domain == "sale" and x._l10n_ar_afip_authorized())
        ):
            raise UserError(
                _("You cannot cancel documents already posted in AFIP (%s).", ",".join(posted_in_afip.mapped("name")))
            )
        return super().button_cancel()

    def _post(self, soft=True):
        # EXTEND account
        """It fixes the rounding on invoice lines to ensure consistency with
        the applied rate (currency is not company currency).This is only applied
        on invoice move types."""
        ar_invoices = self.filtered(
            lambda x: (
                x.company_id.account_fiscal_country_id.code == "AR"
                and x.currency_id != x.company_currency_id
                and x.is_invoice()
            )
        )
        ar_invoice_line_ids = ar_invoices.mapped("invoice_line_ids").ids

        for line in ar_invoices.mapped("line_ids").filtered(
            lambda x: (
                (x.tax_line_id or x.id in ar_invoice_line_ids)
                and x.currency_rate
                and not x.currency_id.is_zero(abs(x.amount_currency) / x.currency_rate - abs(x.balance))
            )
        ):
            balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)
            line.balance = balance
        res = super()._post(soft=soft)
        return res

    @api.model
    def _get_l10n_ar_codes_used_for_inv_and_ref(self):
        return super()._get_l10n_ar_codes_used_for_inv_and_ref() + ["33", "331"]

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if self.journal_id.company_id.account_fiscal_country_id.code == "AR" and self.move_type in [
            "out_refund",
            "in_refund",
        ]:
            # The parent builds: ['|', ('code', 'in', codes)] + ar_domain.
            # In Odoo's prefix notation this parses as (code in codes) OR (first_ar_condition),
            # leaving country_id outside the OR. This lets document types from other LatAm
            # countries that share the same codes (e.g. Chilean doc 33) slip through.
            # AND-ing country_id here ensures only AR document types are returned.
            ar_country_id = self.journal_id.company_id.account_fiscal_country_id.id
            domain = expression.AND([domain, [("country_id", "=", ar_country_id)]])
        return domain
