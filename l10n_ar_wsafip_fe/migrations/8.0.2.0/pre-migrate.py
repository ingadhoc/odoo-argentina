import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('Migrating l10n_ar_wsafip to version %s' % version)
    cr.execute(
        "update ir_model_data set module='l10n_ar_afipws_fe' where module='l10n_ar_wsafip_fe' and name in ('field_account_invoice_afip_cae', 'field_account_invoice_afip_cae_due', 'field_account_invoice_afip_batch_number')")
    cr.execute(
        "update ir_model_data set module='l10n_ar_invoice' where module='l10n_ar_wsafip_fe' and name in ('field_account_invoice_afip_service_end', 'field_account_invoice_afip_service_start')")
