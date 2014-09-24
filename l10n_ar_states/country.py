# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class country(osv.osv):
        _inherit = 'res.country'
        _columns = {
                'afip_code': fields.char('AFIP code', size=64, help='Codigo oficial del AFIP.'),
        }

class country_state(osv.osv):
        _inherit = 'res.country.state'
        _columns = {
                'afip_code': fields.char('AFIP code', size=64, help='Codigo oficial del AFIP.'),
        }

