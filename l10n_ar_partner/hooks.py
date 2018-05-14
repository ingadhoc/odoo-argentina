# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
try:
    from openupgradelib import openupgrade
except ImportError:
    openupgrade = None
import logging
_logger = logging.getLogger(__name__)

# campos renombrados en l10n_ar_invoice
column_renames = {
    'res_partner': [
        ('document_type_id', 'main_id_category_id'),
        ('document_number', 'main_id_number'),
    ],
}


def pre_init_hook(cr):
    _logger.info('Running pre init hook')
    if (
            openupgrade.column_exists(
                cr, 'res_partner', 'document_type_id') and
            not openupgrade.column_exists(
                cr, 'res_partner', 'main_id_category_id')):
        openupgrade.rename_columns(cr, column_renames)
    fix_data_on_l10n_ar_partner(cr)


def fix_data_on_l10n_ar_partner(cr):
    _logger.info('Fixing data on l10nar partner')
    # pasamos de a account_account a l10n_ar_partner
    old_name = 'account_document'
    new_name = 'l10n_ar_partner'

    l10n_ar_partner_data_models = [
        # 'res.partner', al final este es de l10n_ar_account y lo arregla
        # account_document
        'res.partner.id_category',
        'res.partner.title',
    ]

    update_data_module_name(
        cr, l10n_ar_partner_data_models, old_name, new_name)


def update_data_module_name(cr, models, old_name, new_name):
    """
    fix data has been assigend to account_account but is loaded by
    l10n_ar_account
    """
    _logger.info('update_data_module_name')
    for model in models:
        query = ("UPDATE ir_model_data SET module = %s "
                 "WHERE module = %s and model = %s")
        openupgrade.logged_query(cr, query, (new_name, old_name, model))


def post_init_hook(cr, registry):
    """Loaded after installing the module.
    This module's DB modifications will be available.
    :param odoo.sql_db.Cursor cr:
        Database cursor.
    :param odoo.modules.registry.Registry registry:
        Database registry, using v7 api.
    """
    # we don not force dependency on openupgradelib, only if available we try
    # o un de hook
    _logger.info('running post_init_hook')
    if not openupgrade.column_exists:
        return False
    # write en vez de sql para que genere los campos por defecto necesarios
    if openupgrade.column_exists(cr, 'res_partner', 'main_id_number'):
        # we make this so it ise much faster
        _logger.info('creating id numbers records')
        openupgrade.logged_query(cr, """
            INSERT into res_partner_id_number
                (partner_id, category_id, name, sequence, create_uid,
                    write_uid, create_date, write_date, active)
            SELECT id, main_id_category_id, main_id_number, 10, 1, 1,
                create_date, write_date, true
                FROM res_partner
                WHERE main_id_category_id is not null
                    and main_id_number is not null
            """,)
        # tambien con este column exists nos damos cuenta si es migracion
        # si este es el caso y tenia partner_vat_unique tenemos que activar
        # unique
        _logger.info('setting id unique if needed')
        if registry['ir.module.module'].search(cr, 1, [
                ('name', '=', 'partner_vat_unique'),
                ('state', '=', 'to upgrade')]):
            registry['ir.config_parameter'].set_param(
                cr, 1, "l10n_ar_partner.unique_id_numbers", True)
