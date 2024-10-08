from openupgradelib import openupgrade
import logging
logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):

    logger.info('Forzamos la actualización de la vista de report_invoice en módulo l10n_ar para que pueda aplicarse correctamente este cambio https://github.com/odoo/odoo/pull/177283')
    openupgrade.load_data(env.cr, 'l10n_ar', 'views/report_invoice.xml')
