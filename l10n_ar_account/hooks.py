# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp.api import Environment
try:
    from openupgradelib.openupgrade_tools import table_exists
    from openupgradelib.openupgrade_tools import column_exists
    from openupgradelib import openupgrade
except ImportError:
    table_exists = None
    column_exists = None
    openupgradelib = None
import logging
_logger = logging.getLogger(__name__)


def sync_padron_afip(cr, registry):
    """
    Try to sync data from padron
    """
    _logger.info('Syncking afip padron data')
    account_config = registry['account.config.settings']
    account_config_id = account_config.create(
        cr, 1, {})
    try:
        account_config.refresh_taxes_from_padron(cr, 1, account_config_id)
        account_config.refresh_concepts_from_padron(cr, 1, account_config_id)
        account_config.refresh_activities_from_padron(cr, 1, account_config_id)
    except Exception:
        pass


def document_types_not_updatable(cr, registry):
    cr.execute("""
        UPDATE ir_model_data set noupdate=True
        WHERE model = 'account.document.type' and module = 'l10n_ar_account'
    """)


def post_init_hook(cr, registry):
    """Loaded after installing the module.
    This module's DB modifications will be available.
    :param openerp.sql_db.Cursor cr:
        Database cursor.
    :param openerp.modules.registry.RegistryManager registry:
        Database registry, using v7 api.
    """
    _logger.info('Post init hook initialized')

    document_types_not_updatable(cr, registry)
    sync_padron_afip(cr, registry)

    _logger.info('Getting currency rate for invoices')
    ar_invoice_ids = registry['account.invoice'].search(
        cr, 1, [('localization', '=', 'argentina')])
    for invoice_id in ar_invoice_ids:
        vals = registry['account.invoice'].get_localization_invoice_vals(
            cr, 1, invoice_id)
        registry['account.invoice'].write(
            cr, 1, invoice_id, {
                'currency_rate': vals.get('currency_rate')})

    # we don not force dependency on openupgradelib, only if available we try
    # o un de hook
    if not table_exists:
        return False

    # TODO choose:
    # odoo migration delete vouchers that where moved to payments so we make
    # a copy of voucher table and get data from thisone. Beacuse
    # account_payment ids and account_voucher ids does not match, we search
    # by move_id
    advance_column = column_exists(
        cr, 'account_voucher_copy', 'advance_amount')
    if advance_column:
        sql = """
                SELECT receiptbook_id, afip_document_number, advance_amount
                FROM account_voucher_copy
                WHERE move_id = %s
                """
    else:
        sql = """
                SELECT receiptbook_id, afip_document_number
                FROM account_voucher_copy
                WHERE move_id = %s
                """
    if table_exists(cr, 'account_voucher_copy'):
        _logger.info('Migrating vouchers data')
        for payment_id in registry['account.payment'].search(cr, 1, []):
            _logger.info('Migrating vouchers data for payment %s' % payment_id)
            move_ids = registry['account.move'].search(
                cr, 1, [('line_ids.payment_id', '=', payment_id)], limit=1)
            if not move_ids:
                continue
            cr.execute(sql, (move_ids[0],))
            recs = cr.fetchall()
            if recs:
                # steamos el advance_amount aunque sea para los pagos que
                # fueron validados
                if advance_column:
                    receiptbook_id, document_number, advance_amount = recs[0]
                    registry['account.payment'].write(cr, 1, [payment_id], {
                        'receiptbook_id': receiptbook_id,
                        'document_number': document_number,
                        # no lo hacemos aca porque este campo es de
                        # payment.group y el payment group probablemente no
                        # existe en este momento, lo hacemos en l10 withholding
                        # 'unreconciled_amount': advance_amount,
                    })
                else:
                    receiptbook_id, document_number = recs[0]
                    registry['account.payment'].write(cr, 1, [payment_id], {
                        'receiptbook_id': receiptbook_id,
                        'document_number': document_number,
                    })

    # forma horrible de saber si se esta instalando en una bd que viene migrada
    # despues de hacer esto aprendimos a usar el no_version en migrates
    # pero que en realidad tampoco nos anduvo
    env = Environment(cr, 1, {})
    if openupgrade.column_exists(cr, 'account_journal', 'old_type'):
        set_company_loc_ar(cr)
        merge_padron_into_account(cr)
        migrate_responsability_type(env)
        fix_invoice_without_date(env)
    merge_refund_journals_to_normal(env)
    map_tax_groups_to_taxes(cr, registry)


def fix_invoice_without_date(env):
    """
    Odoo does not complete date on invoice on migration, we make it
    """
    _logger.info('Fix invoices without date')
    invoices = env['account.invoice'].search(
        [('move_id', '!=', False), ('date', '=', False)])
    for invoice in invoices:
        invoice.date = invoice.move_id.date


def migrate_responsability_type(env):
    _logger.info('Migrating responsability type to moves')
    cr = env.cr
    openupgrade.logged_query(cr, """
        SELECT afip_responsability_type_id, move_id
        FROM account_invoice
        WHERE move_id is not Null and afip_responsability_type_id is not Null
    """,)
    recs = cr.fetchall()
    for rec in recs:
        afip_responsability_type_id, move_id = rec
        env['account.move'].browse(move_id).afip_responsability_type_id = (
            afip_responsability_type_id)

    invoice_moves = env['account.invoice'].search([
        ('move_id', '!=', False),
        ('afip_responsability_type_id', '!=', False),
    ])
    moves = env['account.move'].search([
        ('id', 'not in', invoice_moves.ids), ('partner_id', '!=', False)])
    moves.set_afip_responsability_type_id()


def merge_padron_into_account(cr):
    _logger.info('Mergin padron module into account')
    openupgrade.update_module_names(
        cr, [('l10n_ar_padron_afip', 'l10n_ar_account')],
        merge_modules=True,)


def set_company_loc_ar(cr):
    _logger.info('Setting loc ar on companies')
    openupgrade.map_values(
        cr,
        # openupgrade.get_legacy_name('type_tax_use'), 'localization',
        'use_argentinian_localization', 'localization',
        # [('all', 'none')],
        [(True, 'argentina')],
        table='res_company', write='sql')


def merge_refund_journals_to_normal(env):
    def get_digits(string):
        try:
            return int(filter(str.isdigit, str(string)))
        except Exception:
            return False

    _logger.info('Merging refund journals to normal ones')
    cr = env.cr

    if openupgrade.column_exists(cr, 'account_journal', 'old_type'):
        journals = env['account.journal']
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
                ('point_of_sale_number', '=', point_of_sale_number),
            ]

            from_journal = journals.browse(from_journal_id)
            to_journals = journals.search(domain)
            # merge journals if we have one coincidence
            if len(to_journals) == 1:
                journals.merge_journals(
                    from_journal, to_journals[0], delete_from=False)
            elif to_journals:
                # merge if number on code is the same on only one
                selected_journal = []
                from_code_number = get_digits(from_journal.code)
                for to_journal in to_journals:
                    to_code_number = get_digits(to_journal.code)
                    if from_code_number == to_code_number:
                        selected_journal.append(to_journal)
                if len(selected_journal) == 1:
                    journals.merge_journals(
                        from_journal, selected_journal[0], delete_from=False)


def map_tax_groups_to_taxes(cr, registry):
    _logger.info('Merging tax groups')
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
