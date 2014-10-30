# -*- coding: utf-8 -*-
from openerp import models, api
from openerp import fields as new_fields
from openerp.osv import fields
import openerp.addons.decimal_precision as dp


class sale_order_line(models.Model):

    """
    En argentina como no se diferencian los impuestos en las facturas, excepto el IVA,
    agrego campos que ignoran el iva solamenta a la hora de imprimir los valores.
    """

    _inherit = "sale.order.line"

    def _printed_prices(self, cr, uid, ids, name, args, context=None):
        res = {}
        tax_obj = self.pool['account.tax']
        cur_obj = self.pool.get('res.currency')

        for line in self.browse(cr, uid, ids, context=context):
            _round = (lambda x: cur_obj.round(
                cr, uid, line.order_id.currency_id, x)) if line.order_id else (lambda x: x)
            quantity = line.product_uom_qty
            discount = line.discount
            printed_price_unit = line.price_unit
            printed_price_net = line.price_unit * \
                (1 - (discount or 0.0) / 100.0)
            printed_price_subtotal = printed_price_net * quantity

            not_vat_taxes = [
                x for x in line.tax_id if x.tax_code_id.parent_id.name != 'IVA']
            taxes = tax_obj.compute_all(cr, uid,
                                        not_vat_taxes, printed_price_net, 1,
                                        product=line.product_id,
                                        partner=line.order_id.partner_id)
            other_taxes_amount = _round(taxes['total_included']) - _round(taxes['total'])

            # TODO: tal vez mejorar esto de que se buscan los iva por el que tiene padre llamado "IVA"
            # Antes habiamos agregado un vampo vat_tax en los code pero el tema es que tambien hay que agregarlo en el template de los tax code y en los planes de cuenta, resulta medio engorroso
            vat_taxes = [
                x for x in line.tax_id if x.tax_code_id.parent_id.name == 'IVA']
            taxes = tax_obj.compute_all(cr, uid,
                                        vat_taxes, printed_price_net, 1,
                                        product=line.product_id,
                                        partner=line.order_id.partner_id)
            vat_amount = _round(taxes['total_included']) - _round(taxes['total'])

            exempt_amount = 0.0
            if not vat_taxes:
                exempt_amount = _round(taxes['total_included'])

            # For document that not discriminate we include the prices
            if line.order_id and not line.order_id.vat_discriminated:
                printed_price_unit = _round(
                    taxes['total_included'] * (1 + (discount or 0.0) / 100.0))
                printed_price_net = _round(taxes['total_included'])
                printed_price_subtotal = _round(
                    taxes['total_included'] * quantity)

            res[line.id] = {
                'price_unit_with_tax': line.price_unit + vat_amount + other_taxes_amount,
                'printed_price_unit': printed_price_unit,
                'printed_price_net': printed_price_net,
                'printed_price_subtotal': printed_price_subtotal,
                'vat_amount': vat_amount,
                'other_taxes_amount': other_taxes_amount,
                'exempt_amount': exempt_amount,
            }
        return res

    _columns = {
        'price_unit_with_tax': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Product Price'),
            string='Unit Price w/ Taxes', multi='printed',),
        'printed_price_unit': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Product Price'),
            string='Unit Price', multi='printed',),
        'printed_price_net': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Product Price'),
            string='Net Price', multi='printed'),
        'printed_price_subtotal': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Product Price'),
            string='Subtotal', multi='printed'),
        'vat_amount': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Vat Amount', multi='printed'),
        'other_taxes_amount': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Other Taxes Amount', multi='printed'),
        'exempt_amount': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Exempt Amount', multi='printed'),
    }


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.one
    @api.depends(
        'partner_id',
        'partner_id.responsability_id',
        'company_id',
        'company_id.partner_id.responsability_id',)
    def get_vat_discriminated(self):
        vat_discriminated = True
        if self.company_id.sale_allow_vat_no_discrimination:
            letter_ids = self.env['account.invoice'].get_valid_document_letters(
                self.partner_id.id, 'sale', self.company_id.id)
            letters = self.env['afip.document_letter'].browse(letter_ids)
            if letters:
                vat_discriminated = letters[0].vat_discriminated
            elif self.company_id.sale_allow_vat_no_discrimination == 'no_discriminate_default':
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

    tax_line = new_fields.Many2many(
        'account.tax',
        compute='get_taxes')
    vat_discriminated = new_fields.Boolean(
        'Discriminate VAT?',
        compute="get_vat_discriminated",
        store=True,
        readonly=False,
        help="Discriminate VAT on Quotations and Sale Orders?")

    def _printed_prices(self, cr, uid, ids, name, args, context=None):
        res = {}

        for order in self.browse(cr, uid, ids, context=context):
            printed_amount_untaxed = order.amount_untaxed
            printed_tax_ids = [x.id for x in order.tax_line]

            vat_amount = sum(
                line.vat_amount for line in order.order_line)
            vat_amount = sum(
                line.vat_amount for line in order.order_line)
            other_taxes_amount = sum(
                line.other_taxes_amount for line in order.order_line)
            exempt_amount = sum(
                line.exempt_amount for line in order.order_line)
            vat_tax_ids = [
                x.id for x in order.tax_line if x.tax_code_id.parent_id.name == 'IVA']

            if not order.vat_discriminated:
                printed_amount_untaxed = sum(
                    line.printed_price_subtotal for line in order.order_line)
                printed_tax_ids = [
                    x.id for x in order.tax_line if x.tax_code_id.parent_id.name != 'IVA']
            res[order.id] = {
                'printed_amount_untaxed': printed_amount_untaxed,
                'printed_tax_ids': printed_tax_ids,
                'vat_tax_ids': vat_tax_ids,
                'printed_amount_tax': order.amount_total - printed_amount_untaxed,
                'vat_amount': vat_amount,
                'other_taxes_amount': other_taxes_amount,
                'exempt_amount': exempt_amount,
            }
        return res

    _columns = {
        'printed_amount_tax': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Tax', multi='printed',),
        'printed_amount_untaxed': fields.function(
            _printed_prices,
            type='float', digits_compute=dp.get_precision('Account'),
            string='Subtotal', multi='printed',),
        'printed_tax_ids': fields.function(
            _printed_prices,
            type='one2many', relation='account.invoice.tax', string='Tax',
            multi='printed'),
        'exempt_amount': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Exempt Amount', multi='printed'),
        'vat_tax_ids': fields.function(
            _printed_prices,
            type='one2many', relation='account.invoice.tax',
            string='VAT Taxes', multi='printed'),
        'vat_amount': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Vat Amount', multi='printed'),
        'other_taxes_amount': fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Other Taxes Amount', multi='printed')
    }
