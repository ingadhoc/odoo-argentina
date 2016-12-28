# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartnerIdNumber(models.Model):
    _inherit = "res.partner.id_number"
    _order = "sequence"

    sequence = fields.Integer(
        default=10,
        required=True,
    )
