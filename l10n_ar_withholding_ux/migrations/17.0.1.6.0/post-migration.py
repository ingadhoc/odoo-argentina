import logging

from odoo.upgrade import util

logger = logging.getLogger(__name__)


def migrate(cr, version):
    logger.info("Forzamos la actualización de la vista res_company_setting.xml en módulo account payment pro")
    util.update_record_from_xml(cr, "account_payment_pro.res_config_settings_view_form")
