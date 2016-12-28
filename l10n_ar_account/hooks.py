# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
try:
    from openupgradelib.openupgrade_tools import table_exists
    from openupgradelib import openupgrade
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
    ar_invoice_ids = registry['account.invoice'].search(
        cr, 1, [('localization', '=', 'argentina')])
    for invoice_id in ar_invoice_ids:
        vals = registry['account.invoice'].get_localization_invoice_vals(
            cr, 1, invoice_id)
        registry['account.invoice'].write(
            cr, 1, invoice_id, {'currency_rate': vals.get('currency_rate')})

    # we don not force dependency on openupgradelib, only if available we try
    # o un de hook
    if not table_exists:
        return False
    # write en vez de sql para que genere los campos por defecto necesarios
    # we where using this but we decide to make it easier and change on v8
    # using related fields
    # query = (
    #     "SELECT aj.id, apos.number, apos.document_sequence_type, apos.type "
    #     "FROM account_journal aj INNER JOIN afip_point_of_sale apos "
    #     "ON aj.point_of_sale_id = apos.id")
    # if table_exists(cr, 'afip_point_of_sale'):
    #     cr.execute(query)
    #     for journal_id, number, doc_sequence_type, type in cr.fetchall():
    #         registry['account.journal'].write(cr, 1, [journal_id], {
    #             'point_of_sale_type': type,
    #             'point_of_sale_number': number,
    #             'document_sequence_type': doc_sequence_type,
    #         })

    # TODO choose:
    # odoo migration delete vouchers that where moved to payments so we make
    # a copy of voucher table and get data from thisone. Beacuse
    # account_payment ids and account_voucher ids does not match, we search
    # by move_id
    if table_exists(cr, 'account_voucher_copy'):
        for payment_id in registry['account.payment'].search(cr, 1, []):
            move_ids = registry['account.move'].search(
                cr, 1, [('line_ids.payment_id', '=', payment_id)], limit=1)
            if not move_ids:
                continue
            cr.execute("""
                SELECT receiptbook_id, afip_document_number
                FROM account_voucher_copy
                WHERE move_id = %s
                """, (move_ids[0],))
            recs = cr.fetchall()
            if recs:
                receiptbook_id, document_number = recs[0]
                registry['account.payment'].write(cr, 1, [payment_id], {
                    'receiptbook_id': receiptbook_id,
                    'document_number': document_number,
                })

    # este era el script para openupgrade
    # if table_exists(cr, 'account_voucher'):
    #     for payment_id in registry['account.payment'].search(cr, 1, []):
    #         cr.execute("""
    #             SELECT receiptbook_id, afip_document_number
    #             FROM account_voucher
    #             WHERE id = %s
    #             """, (payment_id,))
    #         recs = cr.fetchall()
    #         if recs:
    #             receiptbook_id, document_number = recs[0]
    #             registry['account.payment'].write(cr, 1, [payment_id], {
    #                 'receiptbook_id': receiptbook_id,
    #                 'document_number': document_number,
    #             })
    merge_refund_journals_to_normal(cr, registry)
    map_tax_groups_to_taxes(cr, registry)


def merge_refund_journals_to_normal(cr, registry):
    if openupgrade.column_exists(cr, 'account_journal', 'old_type'):
        openupgrade.logged_query(cr, """
            SELECT
                id, point_of_sale_number, old_type, company_id
            FROM
                account_journal
            WHERE old_type in ('sale_refund', 'purchase_refund')
            """,)
        journals_read = cr.fetchall()
        for journal_read in journals_read:
            (
                from_journal_id,
                point_of_sale_number,
                old_type,
                company_id) = journal_read
            new_type = 'sale'
            if old_type == 'purchase_refund':
                new_type = 'purchase'
            domain = [
                ('type', '=', new_type),
                ('id', '!=', from_journal_id),
                ('company_id', '=', company_id),
            ]
            if point_of_sale_number:
                domain += [('point_of_sale_number', '=', point_of_sale_number)]

            journals = registry['account.journal'].search(cr, 1, domain)
            # we only merge journals if we have one coincidence
            if len(journals) == 1:
                from_journal = registry['account.journal'].browse(
                    cr, 1, from_journal_id)
                to_journal = registry['account.journal'].browse(
                    cr, 1, journals[0])
                registry['account.journal'].merge_journals(
                    cr, 1, from_journal, to_journal)


def map_tax_groups_to_taxes(cr, registry):
    if (
            openupgrade.column_exists(cr, 'account_tax', 'tax_code_id') and
            openupgrade.table_exists(cr, 'account_tax_code')):
        # we make an union to add tax without tax code but with base code
        openupgrade.logged_query(cr, """
            SELECT at.id as tax_id, application, afip_code, tax, type
            FROM account_tax at
            INNER JOIN account_tax_code as atc on at.tax_code_id = atc.id
            UNION
            SELECT at.id as tax_id, application, afip_code, tax, type
            FROM account_tax at
            INNER JOIN account_tax_code as atc on at.base_code_id = atc.id and
            at.tax_code_id is null
            """,)
        taxes_read = cr.fetchall()
        for tax_read in taxes_read:
            (
                tax_id,
                application,
                afip_code,
                tax,
                type
            ) = tax_read
            domain = [
                ('application', '=', application),
                ('tax', '=', tax),
                ('type', '=', type),
            ]
            # because only vat and type tax should have afip_code
            if afip_code and tax == 'vat' and type == 'tax':
                domain += [('afip_code', '=', afip_code)]
            tax_group_ids = registry['account.tax.group'].search(cr, 1, domain)
            # we only assign tax group if we found one
            if len(tax_group_ids) == 1:
                registry['account.tax'].write(
                    cr, 1, tax_id, {'tax_group_id': tax_group_ids[0]})
