# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields

class Bank(models.Model)::
    _inherit = 'res.partner.bank'

    cbu = fields.char('CBU', help="Key Bank Uniform"),
