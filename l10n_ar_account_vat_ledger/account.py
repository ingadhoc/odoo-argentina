# -*- coding: utf-8 -*-
from openerp import models, fields, api


class afip_document_class(models.Model):
    _inherit = 'afip.document_class'

    amount_untaxed = fields.Float(
        string='Untaxed',
        compute='_get_amounts',)
    amount_tax = fields.Float(
        string='Tax',
        compute='_get_amounts',)
    amount_total = fields.Float(
        string='total',
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
    def get_amounts(self, vat_ledger):
        domain = [
            ('state', 'not in', ['draft', 'cancel']),
            ('afip_document_class_id', '=', self.id),
            ('journal_id', 'in', vat_ledger.journal_ids.ids),
            ('period_id', '=', vat_ledger.period_id.id)
        ]
        invoices = self.env['account.invoice'].search(domain)
        amount_untaxed = sum([x.amount_untaxed for x in invoices])
        amount_tax = sum([x.amount_tax for x in invoices])
        amount_total = sum([x.amount_total for x in invoices])
        return (amount_untaxed, amount_tax, amount_total)


class account_tax_code(models.Model):
    _inherit = 'account.tax.code'

    amount_untaxed = fields.Float(
        string='Untaxed',
        compute='_get_amounts',)
    amount_tax = fields.Float(
        string='Tax',
        compute='_get_amounts',)

    @api.one
    def _get_amounts(self):
        """
        """
        amount_untaxed = False
        amount_tax = False
        vat_ledger_id = self._context.get('vat_ledger_id', False)
        if vat_ledger_id:
            vat_ledger = self.env['account.vat.ledger'].browse(vat_ledger_id)
            (amount_untaxed, amount_tax) = self.get_amounts(
                vat_ledger)
        self.amount_untaxed = amount_untaxed
        self.amount_tax = amount_tax

    @api.model
    def get_amounts(self, vat_ledger):
        taxes_domain = [
            ('invoice_id', 'in', vat_ledger.invoice_ids.ids),
            ('tax_code_id.id', '=', self.id)]
            # ('tax_code_id.parent_id.name', '=', 'IVA')]
        print 'vat_ledger.invoice_ids.ids', vat_ledger.invoice_ids.ids
        print 'self.id', self.id
        invoice_taxes = self.env['account.invoice.tax'].search(
            taxes_domain)
        amount_untaxed = sum([x.base for x in invoice_taxes])
        amount_tax = sum([x.tax_amount for x in invoice_taxes])
        return (amount_untaxed, amount_tax)


class afip_responsability(models.Model):
    _inherit = 'afip.responsability'

    amount_untaxed = fields.Float(
        string='Untaxed',
        compute='_get_amounts',)
    amount_tax = fields.Float(
        string='Tax',
        compute='_get_amounts',)
    amount_total = fields.Float(
        string='total',
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
    def get_amounts(self, vat_ledger):
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
