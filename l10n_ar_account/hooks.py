# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
try:
    from openupgradelib.openupgrade_tools import table_exists
except ImportError:
    table_exists = None


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
    if not table_exists:
        return False
    # write en vez de sql para que genere los campos por defecto necesarios
    query = (
        "SELECT aj.id, apos.number, apos.document_sequence_type, apos.type "
        "FROM account_journal aj INNER JOIN afip_point_of_sale apos "
        "ON aj.point_of_sale_id = apos.id")
    if table_exists(cr, 'afip_point_of_sale'):
        cr.execute(query)
        for journal_id, number, document_sequence_type, type in cr.fetchall():
            registry['account.journal'].write(cr, 1, [journal_id], {
                'point_of_sale_type': type,
                'point_of_sale_number': number,
                'document_sequence_type': document_sequence_type,
            })

    # TODO borrar o activar, por ahora modificamos openugprade directamente
    # porque borra los account_voucher y perdemos la data
    # migrate voucher data (usamos mismo where que migrador)
    if table_exists(cr, 'account_voucher'):
        for payment_id in registry['account.payment'].search(cr, 1, []):
            cr.execute("""
                SELECT receiptbook_id, afip_document_number
                FROM account_voucher
                WHERE id = %s
                """, (payment_id,))
            recs = cr.fetchall()
            if recs:
                receiptbook_id, document_number = recs[0]
                registry['account.payment'].write(cr, 1, [payment_id], {
                    'receiptbook_id': receiptbook_id,
                    'document_number': document_number,
                })
