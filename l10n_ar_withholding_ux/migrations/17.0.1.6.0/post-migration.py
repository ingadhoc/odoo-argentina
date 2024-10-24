from openupgradelib import openupgrade
import logging

logger = logging.getLogger(__name__)

@openupgrade.migrate()
def migrate(env, version):
    logger.info('Forzamos la actualización de la vista res_company_setting.xml en módulo account payment pro')
    openupgrade.load_data(env, 'account_payment_pro', 'views/res_company_setting.xml')
