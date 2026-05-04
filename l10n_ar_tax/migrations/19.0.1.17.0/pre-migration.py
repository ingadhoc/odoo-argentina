import logging

from odoo import SUPERUSER_ID, api

logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    logger.info("Instalando módulo account_payment_pro_receiptbook como nueva dependencia de l10n_ar_tax")
    module = env["ir.module.module"].search([("name", "=", "account_payment_pro_receiptbook")])
    if module and module.state not in ("installed", "to install", "to upgrade"):
        module.button_install()
