from openerp import models, fields, api
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
        vat_taxes = self.invoice_line_tax_id.filtered(
            lambda r: r.amount and r.tax_code_id.type == 'tax' and r.tax_code_id.tax == 'vat')
            # agregamos el r.amount para que no tenga en cuenta los "exentos"
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
        exempt_vat_taxes = self.invoice_line_tax_id.filtered(
            lambda r: not r.amount and r.tax_code_id.type == 'tax' and r.tax_code_id.tax == 'vat')
        exempt_vat_taxes_amounts = exempt_vat_taxes.compute_all(
            price, 1,
            product=self.product_id,
            partner=self.invoice_id.partner_id)
        exempt_amount = exempt_vat_taxes and exempt_vat_taxes_amounts['total'] or False

        self.vat_amount = vat_taxes_amount * self.quantity
        self.other_taxes_amount = not_vat_taxes_amount * self.quantity
        self.exempt_amount = exempt_amount * self.quantity

    printed_price_unit = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Unit Price'
        )
    printed_price_net = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Net Price',
        )
    printed_price_subtotal = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Subtotal',
        )
    vat_amount = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Vat Amount',
        )
    other_taxes_amount = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Other Taxes Amount',
        )
    exempt_amount = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Exempt Amount',
        )
