# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
# from openerp.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    report_amount_tax = fields.Monetary(
        string='Tax',
        compute='_compute_report_amount_and_taxes'
    )
    report_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_report_amount_and_taxes'
    )
    # report_tax_line_ids = fields.One2many(
    #     compute="_compute_report_amount_and_taxes",
    #     comodel_name='account.invoice.tax',
    #     string='Taxes'
    # )
    vat_discriminated = fields.Boolean(
        compute='_compute_vat_discriminated')

    @api.one
    @api.depends(
        'partner_id',
        'partner_id.afip_responsability_type_id',
        'company_id',
        'company_id.partner_id.afip_responsability_type_id',)
    def _compute_vat_discriminated(self):
        vat_discriminated = True
        company_vat_type = self.company_id.sale_allow_vat_no_discrimination
        if company_vat_type:
            letters = self.env['afip.document_letter']
            if self.company_id.partner_id.afip_responsability_type_id:
                letter_ids = self.env[
                    'account.invoice'].get_valid_document_letters(
                    self.partner_id.id, 'sale', self.company_id.id)
                if letter_ids:
                    letters = letters.browse(letter_ids)
                    vat_discriminated = not letters[0].taxes_included
            # if no responsability or no letters
            if not letters and company_vat_type == 'no_discriminate_default':
                vat_discriminated = False
        self.vat_discriminated = vat_discriminated

    @api.depends(
        'amount_untaxed', 'amount_tax', 'vat_discriminated')
    def _compute_report_amount_and_taxes(self):
        """
        Similar a account_document intoive pero por ahora incluimos o no todos
        los impuestos
        """
        for order in self:
            taxes_included = not self.vat_discriminated
            if not taxes_included:
                report_amount_tax = order.amount_tax
                report_amount_untaxed = order.amount_untaxed
                # not_included_taxes = order.order_line.mapped('tax_id')
            else:
                # not_included_taxes = False
                report_amount_tax = False
                report_amount_untaxed = order.amount_total
            #     not_included_taxes = (
            #         order.tax_line_ids - included_taxes)
            #     report_amount_tax = sum(not_included_taxes.mapped('amount'))
            #     report_amount_untaxed = order.amount_untaxed + sum(
            #         included_taxes.mapped('amount'))
            order.report_amount_tax = report_amount_tax
            order.report_amount_untaxed = report_amount_untaxed
            # order.report_tax_line_ids = not_included_taxes
