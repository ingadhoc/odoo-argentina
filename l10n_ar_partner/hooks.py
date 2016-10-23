# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
try:
    from openupgradelib.openupgrade_tools import column_exists
except ImportError:
    column_exists = None


def post_init_hook(cr, registry):
    """Loaded after installing the module.
    This module's DB modifications will be available.
    :param openerp.sql_db.Cursor cr:
        Database cursor.
    :param openerp.modules.registry.RegistryManager registry:
        Database registry, using v7 api.
    """
    # we don not force dependency on openupgradelib, only if available we try
    # o un de hook
    if not column_exists:
        return False
    # write en vez de sql para que genere los campos por defecto necesarios
    if column_exists(cr, 'res_partner', 'document_number'):
        cr.execute(
            'select id, document_number, main_id_category_id from res_partner')
        for partner_id, document_number, main_id_category_id in cr.fetchall():
            if main_id_category_id and document_number:
                registry['res.partner'].write(
                    cr, 1, [partner_id], {'main_id_number': document_number})
