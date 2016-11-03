# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import SUPERUSER_ID


def load_translations(cr, registry):
    chart_template = registry['ir.model.data'].xmlid_to_object(
        cr, SUPERUSER_ID, 'l10n_be.l10nbe_chart_template')
    chart_template.process_coa_translations()
