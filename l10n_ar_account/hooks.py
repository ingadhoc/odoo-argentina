# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.api import Environment, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


def sync_padron_afip(cr, registry):
    """
    Try to sync data from padron
    """
    _logger.info('Syncking afip padron data')
    env = Environment(cr, SUPERUSER_ID, {})
    try:
        account_config = env['res.config.settings']
        account_config.refresh_from_padron("impuestos")
        account_config.refresh_from_padron("conceptos")
        account_config.refresh_from_padron("actividades")
    except Exception:
        pass


def post_init_hook(cr, registry):
    """Loaded after installing the module.
    This module's DB modifications will be available.
    :param odoo.sql_db.Cursor cr:
        Database cursor.
    :param odoo.modules.registry.Registry registry:
        Database registry, using v7 api.
    """
    _logger.info('Post init hook initialized')
    sync_padron_afip(cr, registry)
