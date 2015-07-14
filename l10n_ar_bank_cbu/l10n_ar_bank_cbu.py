# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp.osv import fields, osv


class Bank(osv.osv):
    _inherit = 'res.partner.bank'
    _columns = {
        'cbu': fields.char('CBU',
                           help="Key Bank Uniform"),
    }
