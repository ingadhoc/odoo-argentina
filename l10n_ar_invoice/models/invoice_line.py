# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp


class account_invoice_line(models.Model):

    """
    En argentina como no se diferencian los impuestos en las facturas, excepto
    el IVA, agrego campos que ignoran el iva solamenta a la hora de imprimir
    los valores.
    """

    _inherit = "account.invoice.line"

    @api.one
    def _get_taxes_and_prices(self):
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)

        price_unit_without_tax = self.invoice_line_tax_id.compute_all(
            self.price_unit, 1, product=self.product_id,
            partner=self.invoice_id.partner_id)

        # For document that not discriminate we include the prices
        if self.invoice_id.vat_discriminated:
            printed_price_unit = price_unit_without_tax['total']
            printed_price_net = price_unit_without_tax['total'] * (
                1 - (self.discount or 0.0) / 100.0)
            printed_price_subtotal = printed_price_net * self.quantity
        else:
            printed_price_unit = price_unit_without_tax['total_included']
            printed_price_net = price_unit_without_tax['total_included'] * (
                1 - (self.discount or 0.0) / 100.0)
            printed_price_subtotal = printed_price_net * self.quantity

        self.printed_price_unit = printed_price_unit
        self.printed_price_net = printed_price_net
        self.printed_price_subtotal = printed_price_subtotal

        # VAT taxes
        if self.invoice_id.type in ('out_invoice', 'in_invoice'):
            vat_taxes = self.invoice_line_tax_id.filtered(
                lambda r: r.tax_code_id.type == 'tax' and r.tax_code_id.tax == 'vat')
        else:   # refunds
            vat_taxes = self.invoice_line_tax_id.filtered(
                lambda r: r.ref_tax_code_id.type == 'tax' and r.ref_tax_code_id.tax == 'vat')
        vat_taxes_amounts = vat_taxes.compute_all(
            price, 1,
            product=self.product_id,
            partner=self.invoice_id.partner_id)
        vat_taxes_amount = vat_taxes_amounts[
            'total_included'] - vat_taxes_amounts['total']

        # Not VAT taxes
        not_vat_taxes = (self.invoice_line_tax_id - vat_taxes)
        not_vat_taxes_amounts = not_vat_taxes.compute_all(
            price, 1,
            product=self.product_id,
            partner=self.invoice_id.partner_id)
        not_vat_taxes_amount = not_vat_taxes_amounts[
            'total_included'] - not_vat_taxes_amounts['total']

        # Exempt VAT taxes (no gravados, 0 y exentos)
        # TODO validar que los excempt ammount sean todos estos o solo algunos
        if self.invoice_id.type in ('out_invoice', 'in_invoice'):
            exempt_vat_taxes = self.invoice_line_tax_id.filtered(
                lambda r: not r.amount and r.tax_code_id.type == 'tax' and r.tax_code_id.tax == 'vat')
        else:   # refunds
            exempt_vat_taxes = self.invoice_line_tax_id.filtered(
                lambda r: not r.amount and r.ref_tax_code_id.type == 'tax' and r.ref_tax_code_id.tax == 'vat')
        exempt_vat_taxes_amounts = exempt_vat_taxes.compute_all(
            price, 1,
            product=self.product_id,
            partner=self.invoice_id.partner_id)
        vat_exempt_amount = exempt_vat_taxes and exempt_vat_taxes_amounts['total'] or False

        self.vat_tax_ids = vat_taxes
        self.vat_amount = vat_taxes_amount * self.quantity
        self.other_taxes_amount = not_vat_taxes_amount * self.quantity
        self.vat_exempt_amount = vat_exempt_amount * self.quantity

    vat_tax_ids = fields.One2many(
        compute="_get_taxes_and_prices",
        comodel_name='account.tax',
        string=_('VAT Taxes')
        )
    printed_price_unit = fields.Float(
        compute="_get_taxes_and_prices",
        digits=dp.get_precision('Product Price'),
        string=_('Unit Price')
        )
    printed_price_net = fields.Float(
        compute="_get_taxes_and_prices",
        digits=dp.get_precision('Product Price'),
        string=_('Net Price'),
        )
    printed_price_subtotal = fields.Float(
        compute="_get_taxes_and_prices",
        digits=dp.get_precision('Account'),
        string=_('Subtotal'),
        )
    vat_amount = fields.Float(
        compute="_get_taxes_and_prices",
        digits=dp.get_precision('Account'),
        string=_('Vat Amount'),
        )
    other_taxes_amount = fields.Float(
        compute="_get_taxes_and_prices",
        digits=dp.get_precision('Account'),
        string=_('Other Taxes Amount'),
        )
    vat_exempt_amount = fields.Float(
        compute="_get_taxes_and_prices",
        digits=dp.get_precision('Account'),
        string=_('Exempt Amount'),
        )
