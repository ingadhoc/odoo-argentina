# -*- coding: utf-8 -*-
from openerp import fields, models


class wsfe_error(models.Model):
    _name = 'afip.wsfe_error'
    _description = 'AFIP WSFE Error'
    name = fields.Char(
        'Name', size=64)
    code = fields.Char(
        'Code', size=2)
    description = fields.Text(
        'Description')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
