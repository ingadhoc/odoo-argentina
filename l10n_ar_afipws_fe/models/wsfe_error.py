# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class WsfeError(models.Model):
    _name = 'afip.wsfe_error'
    _description = 'AFIP WSFE Error'

    name = fields.Char(
        'Name', size=64)
    code = fields.Char(
        'Code', size=2)
    description = fields.Text(
        'Description')
