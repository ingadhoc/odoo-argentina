# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class argentinian_base_configuration(osv.osv_memory):
    _inherit = 'argentinian.base.config.settings'

    _columns = {
        'group_price_unit_with_tax': fields.boolean(
            "Show Unit Price w/ Taxes On sale Order Lines",
            implied_group='l10n_ar_invoice_sale.sale_price_unit_with_tax',),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
