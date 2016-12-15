# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)


# for performance
# TODO this should be suggested to odoo by a PR
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    invoice_id = fields.Many2one(
        auto_join=True
    )


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    invoice_id = fields.Many2one(
        auto_join=True
    )


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # no gravado en iva
    # cc_vat_untaxed = fields.Monetary(
    cc_vat_untaxed_base_amount = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. VAT Untaxed',
    )
    # company currency default odoo fields
    cc_amount_total = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. Total',
    )
    cc_amount_untaxed = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. Untaxed',
    )
    cc_amount_tax = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. Tax',
    )
    # von iva
    cc_vat_amount = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. VAT Amount',
    )
    cc_other_taxes_amount = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. Other Taxes Amount'
    )

    @api.one
    @api.depends('currency_id')
    def _get_currency_values(self):
        # TODO si traer el rate de esta manera no resulta (por ej. porque
        # borran una linea de rate), entonces podemos hacerlo desde el move
        # mas o menos como hace account_invoice_currency o viendo el total de
        # debito o credito de ese mismo
        currency = self.currency_id.with_context(
            date=self.date_invoice or fields.Date.context_today(self))
        if not currency:
            return False
        if self.company_id.currency_id == currency:
            self.cc_amount_untaxed = self.amount_untaxed
            self.cc_amount_tax = self.amount_tax
            self.cc_amount_total = self.amount_total
            self.cc_vat_untaxed_base_amount = self.vat_untaxed_base_amount
            self.cc_vat_amount = self.vat_amount
            self.cc_other_taxes_amount = self.other_taxes_amount
            self.currency_rate = 1.0
        else:
            currency_rate = currency.compute(
                1.0, self.company_id.currency_id, round=False)
            # otra alternativa serua usar currency.compute con round true
            # para cada uno de estos valores
            self.currency_rate = currency_rate
            self.cc_amount_untaxed = currency.round(
                self.amount_untaxed * currency_rate)
            self.cc_amount_tax = currency.round(
                self.amount_tax * currency_rate)
            self.cc_amount_total = currency.round(
                self.amount_total * currency_rate)
            self.cc_vat_untaxed_base_amount = currency.round(
                self.vat_untaxed_base_amount * currency_rate)
            self.cc_vat_amount = currency.round(
                self.vat_amount * currency_rate)
            self.cc_other_taxes_amount = currency.round(
                self.other_taxes_amount * currency_rate)
