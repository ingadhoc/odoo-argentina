# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('Migrating l10n_ar_invoice from version %s' % version)
    cr.execute(
        "update ir_model_data set module='l10n_ar_invoice' where module='l10n_ar_chart_generic' and name = 'partner_afip'")
