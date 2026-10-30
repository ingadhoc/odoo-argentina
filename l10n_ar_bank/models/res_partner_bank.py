from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    clearing_number = fields.Char(compute="_compute_clearing_number", store=True, readonly=False, precompute=True)

    @api.depends("bank_id.bank_number")
    def _compute_clearing_number(self):
        for account in self.filtered("bank_id"):
            account.clearing_number = account.bank_id.bank_number

    def _get_fields_from_bank(self):
        return super()._get_fields_from_bank() + ["clearing_number"]
