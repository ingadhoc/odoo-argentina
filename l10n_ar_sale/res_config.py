# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp.osv import fields, osv


class argentinian_base_configuration(osv.osv_memory):
    _inherit = 'argentinian.base.config.settings'

    _columns = {
        'group_price_unit_with_tax': fields.boolean(
            "Show Unit Price w/ Taxes On sale Order Lines",
            implied_group='l10n_ar_sale.sale_price_unit_with_tax',),
    }
