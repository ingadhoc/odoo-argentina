# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


# TODO mejorar y usar los signos de tax codes para todo (o signo del impuesto)
# en vez de evaluar NC y demas
class afip_document_class(models.Model):
    _inherit = 'afip.document_class'

    amount_untaxed = fields.Float(
        string=_('Untaxed'),
        digits=dp.get_precision('Account'),
        compute='_get_amounts',)
    other_taxes_amount = fields.Float(
        compute="_get_amounts",
        digits=dp.get_precision('Account'),
        string=_('Other Taxes Amount')
    )
    vat_amount = fields.Float(
        compute="_get_amounts",
        digits=dp.get_precision('Account'),
        string=_('VAT Amount')
    )
    amount_total = fields.Float(
        string=_('Total'),
        digits=dp.get_precision('Account'),
        compute='_get_amounts',)

    @api.one
    def _get_amounts(self):
        """
        """
        _logger.info('Getting amounts for document class %s(%s)' % (
            self.name, self.id))
        vat_ledger_id = self._context.get('vat_ledger_id', False)
        if vat_ledger_id:
            vat_ledger = self.env['account.vat.ledger'].browse(vat_ledger_id)
            (
                amount_untaxed, vat_amount,
                other_taxes_amount, amount_total
            ) = self.get_amounts(vat_ledger)
            self.amount_untaxed = amount_untaxed
            self.vat_amount = vat_amount
            self.other_taxes_amount = other_taxes_amount
            self.amount_total = amount_total

    @api.model
    def get_amounts(self, vat_ledger):
        domain = [
            ('state', 'not in', ['draft', 'cancel']),
            ('afip_document_class_id', '=', self.id),
            ('journal_id', 'in', vat_ledger.journal_ids.ids),
            ('period_id', '=', vat_ledger.period_id.id)
        ]
        invoices = self.env['account.invoice'].search(domain)
        amount_untaxed = sum(invoices.mapped('cc_amount_untaxed'))
        vat_amount = sum(invoices.mapped('cc_vat_amount'))
        other_taxes_amount = sum(invoices.mapped('cc_other_taxes_amount'))
        amount_total = sum(invoices.mapped('cc_amount_total'))
        if self.document_type == 'credit_note':
            amount_untaxed = -amount_untaxed
            vat_amount = -vat_amount
            other_taxes_amount = -other_taxes_amount
            amount_total = -amount_total
        return (amount_untaxed, vat_amount, other_taxes_amount, amount_total)


class account_tax_code(models.Model):
    _inherit = 'account.tax.code'

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
        _logger.info('Getting amounts for tax code %s(%s)' % (
            self.name, self.id))
        amount_untaxed = False
        amount_tax = False
        amount_total = False
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
            self, vat_ledger, responsability=False, journal_type=None):
        taxes_domain = [
            ('invoice_id', 'in', vat_ledger.invoice_ids.ids),
            ('invoice_id.state', '!=', 'cancel'),
            ('tax_code_id.id', '=', self.id)]
        if journal_type:
            taxes_domain.append(
                ('invoice_id.journal_id.type', 'in', journal_type))
        if responsability:
            taxes_domain.append(
                ('invoice_id.responsability_id', '=', responsability.id))
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
        # el tema en realidad es que en el reporte queremos mostrarlo positivo
        # tendriamos que hacer alg otipo:
        # for invoice_tax in invoice_taxes:
        #     amount_untaxed += invoice_tax.base_amount * invoice_tax
        # amount_untaxed = abs(sum(invoice_taxes.mapped('base_amount')))
        # amount_tax = abs(sum(invoice_taxes.mapped('tax_amount')))
        amount_untaxed = abs(sum(invoice_taxes.mapped('base_amount'))) - abs(
            sum(refund_invoice_taxes.mapped('base_amount')))
        amount_tax = abs(sum(invoice_taxes.mapped('tax_amount'))) - abs(
            sum(refund_invoice_taxes.mapped('tax_amount')))
        amount_total = amount_untaxed + amount_tax
        return (amount_untaxed, amount_tax, amount_total)


class afip_responsability(models.Model):
    _inherit = 'afip.responsability'

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
        _logger.info('Getting amounts for responsability %s(%s)' % (
            self.name, self.id))
        amount_untaxed = False
        amount_tax = False
        amount_total = False
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
            ('responsability_id', '=', self.id),
            # TODO we should use vat_ledger.invoice_ids
            ('journal_id', 'in', vat_ledger.journal_ids.ids),
            ('period_id', '=', vat_ledger.period_id.id)
        ]
        invoices = self.env['account.invoice'].search(
            domain + [('type', 'in', ['in_invoice', 'out_invoice'])])
        refund_invoices = self.env['account.invoice'].search(
            domain + [('type', 'in', ['in_refund', 'out_refund'])])
        amount_untaxed = sum(invoices.mapped('amount_untaxed')) - sum(
            refund_invoices.mapped('amount_untaxed'))
        amount_tax = sum(invoices.mapped('amount_tax')) - sum(
            refund_invoices.mapped('amount_tax'))
        amount_total = sum(invoices.mapped('amount_total')) - sum(
            refund_invoices.mapped('amount_total'))
        return (amount_untaxed, amount_tax, amount_total)
