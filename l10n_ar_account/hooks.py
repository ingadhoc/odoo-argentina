# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def post_init_hook(cr, registry):
    """Loaded after installing the module.
    This module's DB modifications will be available.
    :param openerp.sql_db.Cursor cr:
        Database cursor.
    :param openerp.modules.registry.RegistryManager registry:
        Database registry, using v7 api.
    """
    # write en vez de sql para que genere los campos por defecto necesarios
    query = (
        "SELECT aj.id, apos.number, apos.document_sequence_type, apos.type "
        "FROM account_journal aj INNER JOIN afip_point_of_sale apos "
        "ON aj.point_of_sale_id = apos.id")
    try:
        cr.execute(query)
        for journal_id, number, document_sequence_type, type in cr.fetchall():
            registry['account.journal'].write(cr, 1, [journal_id], {
                'point_of_sale_type': type,
                'point_of_sale_number': number,
                'document_sequence_type': document_sequence_type,
            })
    except:
        pass
