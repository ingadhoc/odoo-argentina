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
