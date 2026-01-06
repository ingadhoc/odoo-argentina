from odoo import fields, models


class ResBank(models.Model):
    _inherit = "res.bank"

    bank_number = fields.Char(help="The bank number as per the Argentine banking system.")
