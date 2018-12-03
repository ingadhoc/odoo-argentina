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


def document_types_not_updatable(cr, registry):
    _logger.info('Update account.document.type to noupdate=True')
    env = Environment(cr, SUPERUSER_ID, {})
    items = env['ir.model.data'].search([
        ('model', '=', 'account.document.type'),
        ('module', '=', 'l10n_ar_account'),
    ])
    items = items.write({'noupdate': True})


def set_no_monetaria_tag(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    tag = env.ref('l10n_ar_account.no_monetaria_tag')
    xml_ids = [
        'account.data_account_type_non_current_assets',  # Activos no-Corriente
        'account.data_account_type_fixed_assets',  # Activos fijos
        'account.data_account_type_other_income',  # Otros Ingresos
        'account.data_account_type_revenue',  # Ingreso
        'account.data_account_type_expenses',  # Gastos
        'account.data_account_type_depreciation', # Depreciación
        'account.data_account_type_equity', # Capital
        'account.data_account_type_direct_costs',  # Coste de Ingreso
    ]
    account_types = []
    for xml_id in xml_ids:
        account_types.append(env.ref(xml_id).id)
    env['account.account'].search([
        ('user_type_id', 'in', account_types)]).write({
            'tag_ids': [(4, tag.id)],
    })


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
    document_types_not_updatable(cr, registry)
    set_no_monetaria_tag(cr, registry)
