from openupgradelib import openupgrade
import logging

logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    logger.info('Forzamos la actualización de la vista res_partner_view.xml en módulo l10n_ar.')
    openupgrade.load_data(env, 'l10n_ar', 'views/res_partner_view.xml')
