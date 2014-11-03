# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class res_currency(osv.osv):
    _inherit = "res.currency"
    _description = "Currency"

    _columns = {
        'afip_code': fields.char('AFIP Code', size=4, readonly=True),
        'afip_desc': fields.char('AFIP Description', size=250, readonly=True),
        'afip_dt_from': fields.date('AFIP Valid from', readonly=True),
    }
