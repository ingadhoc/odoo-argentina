# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp


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
        amount_untaxed = sum([x.amount_untaxed for x in invoices])
        vat_amount = sum([x.vat_amount for x in invoices])
        other_taxes_amount = sum([x.other_taxes_amount for x in invoices])
        amount_total = sum([x.amount_total for x in invoices])
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
            ('tax_code_id.id', '=', self.id)]
        if journal_type:
            taxes_domain.append(
                ('invoice_id.journal_id.type', 'in', journal_type))
        if responsability:
            taxes_domain.append(
                ('invoice_id.responsability_id', '=', responsability.id))
        invoice_taxes = self.env['account.invoice.tax'].search(
            taxes_domain)
        # we use base_amount and tax_amount instad of base and amount because
        # we want them in local currency
        amount_untaxed = sum([x.base_amount for x in invoice_taxes])
        amount_tax = sum([x.tax_amount for x in invoice_taxes])
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
            ('journal_id', 'in', vat_ledger.journal_ids.ids),
            ('period_id', '=', vat_ledger.period_id.id)
        ]
        invoices = self.env['account.invoice'].search(domain)
        amount_untaxed = sum([x.amount_untaxed for x in invoices])
        amount_tax = sum([x.amount_tax for x in invoices])
        amount_total = sum([x.amount_total for x in invoices])
        return (amount_untaxed, amount_tax, amount_total)
