import logging

from odoo import SUPERUSER_ID, api
from openupgradelib import openupgrade

logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    logger.info(
        """Actualizamos la vista product_view del módulo account para que tome los cambios de este pr https://github.com/odoo/odoo/pull/212225 para poder ver a que compañía corresponde cada impuesto de compras y cada impuesto de ventas en la vista formulario de productos. """
    )
    openupgrade.load_data(env, "account", "views/product_view.xml")
