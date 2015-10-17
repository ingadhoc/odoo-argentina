# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models
import time


class Bank(models.Model):
    _inherit = 'res.bank'
    update_date = fields.Date(
        'Update Date',
        default=lambda *a: time.strftime('%Y-%m-%d'),
        )
    vat = fields.Char(
        'VAT',
        size=32,
        help="Value Added Tax number."
        )
