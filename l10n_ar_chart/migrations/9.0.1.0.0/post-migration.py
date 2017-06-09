# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade
import logging
_logger = logging.getLogger(__name__)


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    _logger.info('Running chart postmigration')
    set_iva_no_corresponde(env)
    migrate_fiscal_positions(env)


def set_iva_no_corresponde(env):
    """
    on v8 we have purchase invioces without vat taxes on lines, now we make it
    mandatory, we fix that
    """
    _logger.info('Setting iva no corresponde')
    for company in env['res.company'].search([]):
        tax_group = env.ref('l10n_ar_account.tax_group_iva_no_corresponde')
        tax = env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('company_id', '=', company.id),
            ('tax_group_id', '=', tax_group.id)], limit=1)
        # TODO asser len tax = 1
        # if not tax we create it
        if not tax:
            # buscamos impuesto de iva 21 para sacar las cuentas contables
            other_vat_tax = env['account.tax'].search([
                ('company_id', '=', company.id),
                ('type_tax_use', '=', 'purchase'),
                ('tax_group_id', '=', env.ref(
                    'l10n_ar_account.tax_group_iva_21').id),
            ], limit=1)

            if not other_vat_tax:
                _logger.error(
                    'No encontramos impuesto la cia %s usa contabilidad '
                    'argentina?!' % company.name)
                continue
            tax = env['account.tax'].create({
                'name': 'IVA Compras No Corresponde',
                'description': 'IVA No Corresponde',
                'amount_type': 'fixed',
                'type_tax_use': 'purchase',
                'account_id': other_vat_tax.account_id.id,
                'refund_account_id': other_vat_tax.refund_account_id.id,
                'company_id': company.id,
                'tax_group_id': tax_group.id,
                'sequence': 2,
                'amount': 0.0,
            })
        lines = env['account.invoice.line'].search([
            ('invoice_id.company_id.localization', '=', 'argentina'),
            ('invoice_line_tax_ids', '=', False),
            ('company_id', '=', company.id),
            ('invoice_id.journal_id.use_documents', '=', True),
            ('invoice_id.type', 'in', ['in_invoice', 'in_refund'])])
        lines.write({'invoice_line_tax_ids': [(6, False, [tax.id])]})
        lines.mapped('invoice_id').compute_taxes()


def migrate_fiscal_positions(env):
    """
    En v8 las pos fiscales se creaban por data pero en account_document, para
    que no se borren porque a veces estaban con no update, les borrabamos el
    ext id, ademas se generaban sin cia y entonces pueden estar compartidas,
    por eso las desactivamos y generamos nuevas intenando mapear
    taxes por tax groups
    """
    # desactivamos las viejas
    depreceated_fps = env['account.fiscal.position'].search(
        [('afip_code', '!=', False)])
    depreceated_fps.write({'active': False})
    # delete properties of deactived fp
    values = ['%s,%s' % (
        'account.fiscal.position', id) for id in depreceated_fps.ids]
    env['ir.property'].search([('value_reference', 'in', values)]).unlink()

    # solo creamos posiciones fiscales si tiene chart seteado
    for company in env['res.company'].search(
            [('chart_template_id', '!=', False)]):
        ri_chart = env.ref('l10n_ar_chart.l10nar_ri_chart_template')
        positions = env['account.fiscal.position.template'].search(
            [('chart_template_id', '=', ri_chart.id)])
        for position in positions:
            new_fp = env['account.fiscal.position'].create({
                'company_id': company.id,
                'afip_code': position.afip_code,
                'auto_apply': position.auto_apply,
                'afip_responsability_type_ids': [
                    (6, False, position.afip_responsability_type_ids.ids)],
                'name': position.name,
                'note': position.note})
            for tax in position.tax_ids:
                tax_source = env['account.tax'].search([
                    ('company_id', '=', company.id),
                    ('tax_group_id', '=', tax.tax_src_id.tax_group_id.id),
                    ('type_tax_use', '=', tax.tax_src_id.type_tax_use),
                ], limit=1)
                tax_dest = env['account.tax'].search([
                    ('company_id', '=', company.id),
                    ('tax_group_id', '=', tax.tax_dest_id.tax_group_id.id),
                    ('type_tax_use', '=', tax.tax_dest_id.type_tax_use),
                ], limit=1)
                # only tax_source required
                if tax_source:
                    env['account.fiscal.position.tax'].create({
                        'tax_src_id': tax_source.id,
                        'tax_dest_id': tax_dest.id,
                        'position_id': new_fp.id
                    })
