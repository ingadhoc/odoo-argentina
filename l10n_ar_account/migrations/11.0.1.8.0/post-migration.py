from openupgradelib import openupgrade
import logging

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    _logger.info('Moving arba_cit field to l10n_ar_account')
    _xmlid_renames = [
        ('l10n_ar_account_withholding.field_res_company_arba_cit',
        'l10n_ar_account.field_res_company_arba_cit'),
        ('l10n_ar_account_withholding.field_res_config_settings_arba_cit',
        'l10n_ar_account.field_res_config_settings_arba_cit'),
    ]
    openupgrade.rename_xmlids(env.cr, _xmlid_renames)
