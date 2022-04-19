from openupgradelib import openupgrade
import logging

logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    logger.info('Forzamos la actualizacion del modulo l10n_ar que cambio vista xml pero no version del manifest')
    openupgrade.load_data(
        env.cr, 'l10n_ar', 'views/res_partner_view.xml')
