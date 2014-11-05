# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class afip_country(osv.osv):
    _inherit = 'res.country'

    _columns = {
        'cuit_fisica': fields.char('CUIT persona fisica', size=11),
        'cuit_juridica': fields.char('CUIT persona juridica', size=11),
        'cuit_otro': fields.char('CUIT otro', size=11),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
