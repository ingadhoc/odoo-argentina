# -*- coding: utf-8 -*-
from odoo import models, fields


class AfipVatF2002Category(models.Model):
    _name = "afip.vat.f2002_category"

    name = fields.Char(
        required=True,
    )
