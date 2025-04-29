import logging

from odoo import SUPERUSER_ID, api

logger = logging.getLogger(__name__)


def migrate(cr, version):
    logger.info("Forzamos la actualización de la moneda Dolar para que tenga USD como simbolo")
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("base.USD").symbol = "USD"
