# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
# from openerp.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    report_price_unit = fields.Monetary(
        string='Unit Price',
        compute='_compute_report_prices_and_taxes'
    )
    price_unit_with_tax = fields.Monetary(
        string='Price Unit Price',
        compute='_compute_report_prices_and_taxes'
    )
    report_price_subtotal = fields.Monetary(
        string='Amount',
        compute='_compute_report_prices_and_taxes'
    )
    report_price_net = fields.Monetary(
        string='Net Amount',
        compute='_compute_report_prices_and_taxes'
    )
    report_tax_id = fields.One2many(
        compute="_compute_report_prices_and_taxes",
        comodel_name='account.tax',
        string='Taxes'
    )

    @api.multi
    @api.depends(
        'price_unit',
        'price_subtotal',
        'order_id.vat_discriminated'
    )
    def _compute_report_prices_and_taxes(self):
        """
        Similar a account_document pero por ahora inluimos o no todos los
        impuestos
        """
        for line in self:
            order = line.order_id
            taxes_included = not order.vat_discriminated
            if not taxes_included:
                report_price_unit = line.price_unit
                report_price_subtotal = line.price_subtotal
                not_included_taxes = line.tax_id
                price_unit_with_tax = line.tax_id.compute_all(
                    line.price_unit, order.currency_id, 1.0, line.product_id,
                    order.partner_id)['total_included']
            else:
                included_taxes = line.tax_id
                not_included_taxes = (
                    line.tax_id - included_taxes)
                report_price_unit = included_taxes.compute_all(
                    line.price_unit, order.currency_id, 1.0, line.product_id,
                    order.partner_id)['total_included']
                report_price_subtotal = report_price_unit * line.quantity

            report_price_net = report_price_unit * (
                1 - (line.discount or 0.0) / 100.0)

            line.price_unit_with_tax = price_unit_with_tax
            line.report_price_subtotal = report_price_subtotal
            line.report_price_unit = report_price_unit
            line.report_price_net = report_price_net
            line.report_tax_id = not_included_taxes
