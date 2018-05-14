# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # for performance (should be a PR to odoo)
    tax_group_id = fields.Many2one(
        auto_join=True
    )


class AcountDocumentType(models.Model):
    _inherit = 'account.document.type'

    amount_untaxed = fields.Monetary(
        string='Untaxed',
        compute='_get_amounts',
    )
    other_taxes_amount = fields.Monetary(
        compute="_get_amounts",
        string='Other Taxes Amount'
    )
    vat_amount = fields.Monetary(
        compute="_get_amounts",
        string='VAT Amount'
    )
    amount_total = fields.Monetary(
        string='Total',
        compute='_get_amounts',
    )
    currency_id = fields.Many2one(
        'res.currency',
        compute='_get_amounts'
    )

    @api.one
    def _get_amounts(self):
        """
        """
        _logger.info('Getting amounts for document type %s(%s)' % (
            self.name, self.id))
        vat_ledger_id = self._context.get('vat_ledger_id', False)
        if vat_ledger_id:
            vat_ledger = self.env['account.vat.ledger'].browse(vat_ledger_id)
            (
                amount_untaxed, vat_amount,
                other_taxes_amount, amount_total
            ) = self.get_amounts(vat_ledger)
            self.currency_id = vat_ledger.company_id.currency_id
            self.amount_untaxed = amount_untaxed
            self.vat_amount = vat_amount
            self.other_taxes_amount = other_taxes_amount
            self.amount_total = amount_total

    @api.model
    def get_amounts(self, vat_ledger):
        domain = [
            ('state', 'not in', ['draft', 'cancel']),
            ('document_type_id', '=', self.id),
            ('id', 'in', vat_ledger.invoice_ids.ids),
            # ('journal_id', 'in', vat_ledger.journal_ids.ids),
            # ('period_id', '=', vat_ledger.period_id.id)
        ]
        invoices = self.env['account.invoice'].search(domain)
        amount_untaxed = sum(invoices.mapped('cc_amount_untaxed'))
        vat_amount = sum(invoices.mapped('cc_vat_amount'))
        other_taxes_amount = sum(invoices.mapped('cc_other_taxes_amount'))
        amount_total = sum(invoices.mapped('cc_amount_total'))
        if self.internal_type == 'credit_note':
            amount_untaxed = -amount_untaxed
            vat_amount = -vat_amount
            other_taxes_amount = -other_taxes_amount
            amount_total = -amount_total
        return (amount_untaxed, vat_amount, other_taxes_amount, amount_total)


class account_tax(models.Model):
    _inherit = 'account.tax'

    amount_untaxed = fields.Float(
        string='Untaxed',
        compute='_get_amounts',
    )
    amount_tax = fields.Float(
        string='Tax',
        compute='_get_amounts',
    )
    amount_total = fields.Float(
        string='Total',
        compute='_get_amounts',
    )

    @api.one
    def _get_amounts(self):
        """
        """
        amount_untaxed = False
        amount_tax = False
        amount_total = False
        _logger.info('Getting amounts for tax %s(%s)' % (
            self.name, self.id))
        vat_ledger_id = self._context.get('vat_ledger_id', False)
        if vat_ledger_id:
            vat_ledger = self.env['account.vat.ledger'].browse(vat_ledger_id)
            (amount_untaxed, amount_tax, amount_total) = self.get_amounts(
                vat_ledger)
        self.amount_untaxed = amount_untaxed
        self.amount_tax = amount_tax
        self.amount_total = amount_total

    @api.model
    def get_amounts(
            self, vat_ledger, responsability=False, invoice_type=None):
        taxes_domain = [
            ('invoice_id', 'in', vat_ledger.invoice_ids.ids),
            ('invoice_id.state', '!=', 'cancel'),
            ('tax_id.id', '=', self.id)]
        if invoice_type:
            taxes_domain.append(
                ('invoice_id.type', 'in', invoice_type))
        if responsability:
            taxes_domain.append(
                ('invoice_id.afip_responsability_type_id',
                    '=', responsability.id))
        # invoice_taxes = self.env['account.invoice.tax'].search(
        #     taxes_domain)
        invoice_taxes = self.env['account.invoice.tax'].search(
            taxes_domain +
            [('invoice_id.type', 'in', ['in_invoice', 'out_invoice'])])
        refund_invoice_taxes = self.env['account.invoice.tax'].search(
            taxes_domain +
            [('invoice_id.type', 'in', ['in_refund', 'out_refund'])])
        # we use base_amount and tax_amount instad of base and amount because
        # we want them in local currency
        # usamos valor absoluto porque si el impuesto se configura con signo
        # negativo, por ej. para notas de credito, nosotros igual queremos
        # llevarlo positivo
        # TODO mejorarlo, no hace falta si lo disenamos bien, el tema es que
        # algunos usan regitrando esto como negativo y otros como positivo
        # el tema en realidad es que en el reporte queremos mostrarlo
        # positivo tendriamos que hacer alg otipo:
        # for invoice_tax in invoice_taxes:
        #     amount_untaxed += invoice_tax.base_amount * invoice_tax
        # amount_untaxed = abs(sum(invoice_taxes.mapped('base_amount')))
        # amount_tax = abs(sum(invoice_taxes.mapped('tax_amount')))
        amount_untaxed = abs(sum(invoice_taxes.mapped('cc_base'))) - abs(
            sum(refund_invoice_taxes.mapped('cc_base')))
        amount_tax = abs(sum(invoice_taxes.mapped('cc_amount'))) - abs(
            sum(refund_invoice_taxes.mapped('cc_amount')))
        amount_total = amount_untaxed + amount_tax
        return (amount_untaxed, amount_tax, amount_total)


class AfipResponsabilityType(models.Model):
    _inherit = 'afip.responsability.type'

    amount_untaxed = fields.Float(
        string=_('Untaxed'),
        compute='_get_amounts',)
    amount_tax = fields.Float(
        string=_('Tax'),
        compute='_get_amounts',)
    amount_total = fields.Float(
        string=_('Total'),
        compute='_get_amounts',)

    @api.one
    def _get_amounts(self):
        """
        """
        amount_untaxed = False
        amount_tax = False
        amount_total = False
        _logger.info('Getting amounts for responsability %s(%s)' % (
            self.name, self.id))
        vat_ledger_id = self._context.get('vat_ledger_id', False)
        if vat_ledger_id:
            vat_ledger = self.env['account.vat.ledger'].browse(vat_ledger_id)
            (amount_untaxed, amount_tax, amount_total) = self.get_amounts(
                vat_ledger)
        self.amount_untaxed = amount_untaxed
        self.amount_tax = amount_tax
        self.amount_total = amount_total

    @api.model
    def get_amounts(self, vat_ledger, tax_code=False):
        domain = [
            ('state', 'not in', ['draft', 'cancel']),
            ('afip_responsability_type_id', '=', self.id),
            # TODO we should use vat_ledger.invoice_ids
            ('id', 'in', vat_ledger.invoice_ids.ids),
            # ('journal_id', 'in', vat_ledger.journal_ids.ids),
            # ('period_id', '=', vat_ledger.period_id.id)
        ]
        invoices = self.env['account.invoice'].search(
            domain + [('type', 'in', ['in_invoice', 'out_invoice'])])
        refund_invoices = self.env['account.invoice'].search(
            domain + [('type', 'in', ['in_refund', 'out_refund'])])
        amount_untaxed = sum(invoices.mapped('cc_amount_untaxed')) - sum(
            refund_invoices.mapped('cc_amount_untaxed'))
        amount_tax = sum(invoices.mapped('cc_amount_tax')) - sum(
            refund_invoices.mapped('cc_amount_tax'))
        amount_total = sum(invoices.mapped('cc_amount_total')) - sum(
            refund_invoices.mapped('cc_amount_total'))
        return (amount_untaxed, amount_tax, amount_total)
