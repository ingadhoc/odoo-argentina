import ast
import re

from dateutil.relativedelta import relativedelta
from odoo import api, models

from .res_company_jurisdiction_padron import PARP_CONTRIBUTOR_MULTILATERAL

# Only Santa Fe reports the taxpayer regime in its padron. Elsewhere iibb_total is a regular
# configured base (e.g. Neuquén) and must not be filtered on.
SANTA_FE_JURISDICTION_CODE = "921"

IIBB_TAX_TYPES = ("iibb_untaxed", "iibb_total")

# Marks the total-base (Multilateral Agreement) variant created from a net-base tax.
IIBB_TOTAL_TAX_NAME_SUFFIX = "CM"

# The native flow calls _ensure_tax with the rate only.
PADRON_TAX_TYPE_CONTEXT_KEY = "l10n_ar_padron_tax_type"


class AccountFiscalPositionL10nArTax(models.Model):
    _inherit = "account.fiscal.position.l10n_ar_tax"

    def _padron_defines_base(self):
        self.ensure_one()
        return (
            self.tax_type == "withholding"
            and self.default_tax_id.l10n_ar_state_id.jurisdiction_code == SANTA_FE_JURISDICTION_CODE
        )

    def _get_parp_tax_type(self, contributor_type):
        """Withholding base for a PARP contributor type, False to keep the configured one.

        Only 'C' changes the base: forcing the net base on a local would override a total
        base configured on purpose.
        """
        self.ensure_one()
        if self.tax_type != "withholding":
            return False
        return "iibb_total" if contributor_type == PARP_CONTRIBUTOR_MULTILATERAL else False

    def _get_padron_tax_type(self, partner, date):
        """Base requested by the padron for the partner, False if none."""
        self.ensure_one()
        # the base only applies when the rate also comes from the padron
        if self.webservice != "padron" or not self._padron_defines_base():
            return False
        padron_file = self._search_padron_file(self.default_tax_id.l10n_ar_state_id, date)
        if not padron_file:
            return False
        return self._get_parp_tax_type(padron_file._get_parp_contributor_type(partner.vat))

    def _get_configured_tax_type(self):
        """Base of the line's default tax; an empty base counts as net."""
        self.ensure_one()
        base = self.default_tax_id.l10n_ar_tax_type
        return base if base in IIBB_TAX_TYPES else "iibb_untaxed"

    def _get_tax_type_domain(self, l10n_ar_tax_type):
        if l10n_ar_tax_type == "iibb_untaxed":
            return [("l10n_ar_tax_type", "in", ["iibb_untaxed", False])]
        return [("l10n_ar_tax_type", "=", l10n_ar_tax_type)]

    @api.depends("fiscal_position_id", "tax_type")
    def _compute_tax_template_domain(self):
        """Hide the CM variant: picking it by hand would give the total base to locals too."""
        super()._compute_tax_template_domain()
        for rec in self:
            rec.tax_template_domain = ast.literal_eval(rec.tax_template_domain or "[]") + [
                "!",
                "&",
                ("l10n_ar_tax_type", "=", "iibb_total"),
                ("name", "=like", f"% {IIBB_TOTAL_TAX_NAME_SUFFIX}"),
            ]

    def _get_tax_from_ws(self, partner, date):
        self.ensure_one()
        # same date the native flow uses to search the padron
        tax_type = self._get_padron_tax_type(partner, date + relativedelta(day=1))
        rec = self.with_context(**{PADRON_TAX_TYPE_CONTEXT_KEY: tax_type}) if tax_type else self
        return super(AccountFiscalPositionL10nArTax, rec)._get_tax_from_ws(partner, date)

    def _ensure_tax(self, rate, l10n_ar_tax_type=None):
        """Same as native, but the base is part of the tax lookup."""
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
        template_tax = self.default_tax_id
        if "%" not in template_tax.name:
            name = f"{template_tax.name} {rate}%"
        else:
            name = re.sub(r"\b\d+(\.\d+)?\s*%", f"{rate}%", template_tax.name)
        if base == "iibb_total" and template_tax.l10n_ar_tax_type != "iibb_total":
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
