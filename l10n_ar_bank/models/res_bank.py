from odoo import fields, models


class ResBank(models.Model):
    _inherit = "res.bank"
    _rec_names_search = ["name", "bic", "bank_number"]

    bank_number = fields.Char(index=True, help="The bank number as per the Argentine banking system.")
