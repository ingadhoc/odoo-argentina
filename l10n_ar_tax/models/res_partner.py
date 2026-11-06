from dateutil.relativedelta import relativedelta
from odoo import fields, models
from odoo.addons.l10n_ar_withholding.models.account_tax import EARNINGS_TAX_TYPES
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = "res.partner"

    # TODO Borrar? lo estamos usando?
    drei = fields.Selection(
        [
            ("activo", "Activo"),
            ("no_activo", "No Activo"),
        ],
        string="DREI",
    )
    l10n_ar_partner_tax_ids = fields.One2many(
        domain=[("tax_id.type_tax_use", "=", "purchase"), ("tax_id.is_withholding_tax", "=", True)]
    )
    l10n_ar_partner_perception_ids = fields.One2many(
        "l10n_ar.partner.tax",
        "partner_id",
        "Argentinean Perception Taxes",
        domain=[("tax_id.type_tax_use", "=", "sale"), ("tax_id.is_withholding_tax", "=", False)],
    )

    def _l10n_ar_get_period_accumulation(self, tax, date, exclude_payment=None):
        """Same accumulation as before 20.0: the whole legal entity (the company domain of account_ux, not the company
        tree) and from the first day of the month to the date of the payment, not to the end of the month."""
        self.ensure_one()
        domain = Domain(
            [
                *self.env["account.move.line"]._check_company_domain(tax.company_id),
                ("parent_state", "=", "posted"),
                ("date", ">=", date + relativedelta(day=1)),
                ("date", "<=", date),
                ("partner_id", "=", self.commercial_partner_id.id),
            ]
        )
        if exclude_payment:
            domain &= Domain("payment_id", "!=", exclude_payment.id)
        regime_domain = Domain("l10n_ar_withholding_tax_type", "in", list(EARNINGS_TAX_TYPES)) & (
            Domain("l10n_ar_code", "=", tax.l10n_ar_code) if tax.l10n_ar_code else Domain("id", "=", tax.id)
        )
        AccountMoveLine = self.env["account.move.line"].sudo()
        withheld = AccountMoveLine._read_group(
            domain & Domain("tax_line_id", "any", regime_domain), ["partner_id"], ["balance:sum"]
        )
        bases = AccountMoveLine._read_group(
            domain & Domain("tax_ids", "any", regime_domain), ["partner_id"], ["balance:sum"]
        )
        return {
            "base": abs(bases[0][1]) if bases else 0.0,
            "withheld": abs(withheld[0][1]) if withheld else 0.0,
            "currency": tax.company_id.currency_id,
        }
