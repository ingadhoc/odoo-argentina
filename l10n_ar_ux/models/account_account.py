from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    l10n_ar_afip_activity_id = fields.Many2one(
        "afip.activity",
        string="Associated Activity",
        help="Activity associated with this account. If not set, the company's default activity will be used.",
    )
