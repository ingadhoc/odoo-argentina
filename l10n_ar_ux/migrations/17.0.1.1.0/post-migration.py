import logging

from odoo import SUPERUSER_ID, api
from openupgradelib import openupgrade

logger = logging.getLogger(__name__)


def migrate(cr, version):
    logger.info("Forzamos la actualización de la vista res_partner_view.xml en módulo l10n_ar.")
    env = api.Environment(cr, SUPERUSER_ID, {})
    openupgrade.load_data(env, "l10n_ar", "views/res_partner_view.xml")
