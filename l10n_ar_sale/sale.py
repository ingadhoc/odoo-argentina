# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
import openerp.addons.decimal_precision as dp


class sale_order_line(models.Model):

    """
    En argentina como no se diferencian los impuestos en las facturas, excepto
    el IVA, agrego campos que ignoran el iva solamenta a la hora de imprimir
    los valores. Extendemos dicha funcionalidad a las ordenes de venta
    """

    _inherit = "sale.order.line"

    @api.one
    def _printed_prices(self):
        taxes = self.env['account.tax']

        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)

        price_unit_without_tax = self.tax_id.compute_all(
            self.price_unit, 1, product=self.product_id,
            partner=self.order_id.partner_id)

        price_unit_with_tax = price_unit_without_tax['total_included']
        # For document that not discriminate we include the prices
        if self.order_id.vat_discriminated:
            printed_price_unit = price_unit_without_tax['total']
            printed_price_net = price_unit_without_tax['total'] * (
                1 - (self.discount or 0.0) / 100.0)
            printed_price_subtotal = printed_price_net * self.product_uom_qty
        else:
            printed_price_unit = price_unit_without_tax['total_included']
            printed_price_net = price_unit_without_tax['total_included'] * (
                1 - (self.discount or 0.0) / 100.0)
            printed_price_subtotal = printed_price_net * self.product_uom_qty

        self.printed_price_unit = printed_price_unit
        self.printed_price_net = printed_price_net
        self.printed_price_subtotal = printed_price_subtotal
        # Not VAT taxes
        not_vat_taxes = self.tax_id.filtered(
            lambda r: r.tax_code_id.parent_id.name != 'IVA').compute_all(
            price, 1,
            product=self.product_id,
            partner=self.order_id.partner_id)
        not_vat_taxes_amount = not_vat_taxes[
            'total_included'] - not_vat_taxes['total']

        # VAT taxes
        vat_taxes = self.tax_id.filtered(
            lambda r: r.tax_code_id.parent_id.name == 'IVA').compute_all(
            price, 1,
            product=self.product_id,
            partner=self.order_id.partner_id)
        vat_taxes_amount = vat_taxes['total_included'] - vat_taxes['total']

        exempt_amount = 0.0
        if not vat_taxes:
            exempt_amount = taxes['total_included']

        self.price_unit_with_tax = price_unit_with_tax
        self.vat_amount = vat_taxes_amount * self.product_uom_qty
        self.other_taxes_amount = not_vat_taxes_amount * self.product_uom_qty
        self.exempt_amount = exempt_amount * self.product_uom_qty

    price_unit_with_tax = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Unit Price w/ Taxes')
        )
    printed_price_unit = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Unit Price')
        )
    printed_price_net = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Net Price'),
        )
    printed_price_subtotal = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Subtotal'),
        )
    vat_amount = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Vat Amount'),
        )
    other_taxes_amount = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Other Taxes Amount'),
        )
    exempt_amount = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Exempt Amount'),
        )


class sale_order(models.Model):
    _inherit = "sale.order"

    # no podemos usar onchange porque ya hay onchange de api vieja sobre partner'
    @api.one
    @api.depends(
        'partner_id',
        'partner_id.responsability_id',
        'company_id',
        'company_id.partner_id.responsability_id',)
    def get_vat_discriminated(self):
        vat_discriminated = True
        if self.company_id.sale_allow_vat_no_discrimination:
            letters = self.env['afip.document_letter']
            if self.company_id.partner_id.responsability_id:
                letter_ids = self.env['account.invoice'].get_valid_document_letters(
                    self.partner_id.id, 'sale', self.company_id.id)
                if letter_ids:
                    letters = letters.browse(letter_ids)
                    vat_discriminated = letters[0].vat_discriminated
            # if no responsability or no letters
            if not letters and self.company_id.sale_allow_vat_no_discrimination == 'no_discriminate_default':
                vat_discriminated = False
        self.vat_discriminated = vat_discriminated

    @api.one
    @api.depends(
        'partner_id',
        'partner_id.responsability_id',
        'company_id',
        'company_id.partner_id.responsability_id',)
    def get_taxes(self):
        self.tax_line = self.env['account.tax']
        tax_ids = []
        for line in self.order_line:
            tax_ids += line.tax_id.ids
        tax_ids = list(set(tax_ids))
        self.tax_line = tax_ids

    tax_line = fields.Many2many(
        'account.tax',
        compute='get_taxes')
    vat_discriminated = fields.Boolean(
        _('Discriminate VAT?'),
        compute="get_vat_discriminated",
        help=_("Discriminate VAT on Quotations and Sale Orders?"))

    @api.one
    def _printed_prices(self):
        vat_amount = sum(
            line.vat_amount for line in self.order_line)
        other_taxes_amount = sum(
            line.other_taxes_amount for line in self.order_line)
        exempt_amount = sum(
            line.exempt_amount for line in self.order_line)
        vat_tax_ids = [
            x.id for x in self.tax_line if x.tax_code_id.parent_id.name == 'IVA']

        if self.vat_discriminated:
            printed_amount_untaxed = self.amount_untaxed
            printed_tax_ids = [x.id for x in self.tax_line]
        else:
            printed_amount_untaxed = self.amount_total
            # printed_amount_untaxed = sum(
            #     line.printed_price_subtotal for line in self.order_line)
            # por ahora hacemos que no se imprima ninguno
            printed_tax_ids = []
            # printed_tax_ids = [
            #         x.id for x in self.tax_line if x.tax_code_id.parent_id.name != 'IVA']

        self.printed_amount_untaxed = printed_amount_untaxed
        self.printed_tax_ids = printed_tax_ids
        self.printed_amount_tax = self.amount_total - printed_amount_untaxed
        self.vat_tax_ids = vat_tax_ids
        self.vat_amount = vat_amount
        self.other_taxes_amount = other_taxes_amount
        self.exempt_amount = exempt_amount

    printed_amount_tax = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Tax')
        )
    printed_amount_untaxed = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Subtotal')
        )
    exempt_amount = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Exempt Amount')
        )
    vat_amount = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Vat Amount')
        )
    other_taxes_amount = fields.Float(
        compute="_printed_prices",
        digits=dp.get_precision('Account'),
        string=_('Other Taxes Amount')
        )
    printed_tax_ids = fields.One2many(
        compute="_printed_prices",
        comodel_name='account.invoice.tax',
        string=_('Tax')
        )
    vat_tax_ids = fields.One2many(
        compute="_printed_prices",
        comodel_name='account.invoice.tax',
        string=_('VAT Taxes')
        )
