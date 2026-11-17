##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    l10n_ar_apply_withholding = fields.Boolean(
        string="Apply Withholdings",
        default=True,
        help="If enabled, payments made with this payment method compute withholdings automatically. "
        "If disabled, the fiscal position is forced to empty so that no withholdings are computed "
        "(e.g. credit card or petty cash payments).",
    )

    def write(self, vals):
        # Turning the flag off recomputes the fiscal position of the drafts that use this method, and
        # that recompute cannot fix their amount: it is restored here, outside of it.
        payments = self.env["account.payment"]
        if "l10n_ar_apply_withholding" in vals and not vals["l10n_ar_apply_withholding"]:
            payments = payments.search(
                [
                    ("payment_method_line_id", "in", self.ids),
                    ("state", "=", "draft"),
                    ("l10n_ar_fiscal_position_id", "!=", False),
                ]
            )
        withheld = payments._l10n_ar_get_withheld_amounts()
        res = super().write(vals)
        payments._l10n_ar_restore_withheld_amounts(withheld)
        return res
