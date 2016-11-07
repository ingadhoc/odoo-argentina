# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class argentinian_base_configuration(models.Model):
    _inherit = 'argentinian.base.config.settings'

    group_price_unit_with_tax = fields.Boolean(
        "Show Unit Price w/ Taxes On sale Order Lines",
        implied_group='l10n_ar_sale.sale_price_unit_with_tax',)
