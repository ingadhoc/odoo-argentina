from odoo import models, fields


class AfipVatF2002_category(models.Model):
    _name = "afip.vat.f2002_category"

    name = fields.Char(
        required=True,
    )
