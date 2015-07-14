import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('Migrating l10n_ar_invoice from version %s' % version)
    cr.execute(
        "update ir_model_data set module='l10n_ar_invoice' where module='l10n_ar_chart_generic' and name = 'partner_afip'")
