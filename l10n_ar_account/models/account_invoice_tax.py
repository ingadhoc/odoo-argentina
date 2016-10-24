# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
# from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)

# TODO borrar, ahora odoo agrego el campo base computado

# class AccountInvoiceTax(models.Model):
#     _inherit = "account.invoice.tax"
#     """
#     We need this fields for electronic invoice, vat reports and citi
#     """
#     base_amount = fields.Monetary(
#         compute="_get_base_amount",
#         string='Base Amount'
#     )

#     @api.multi
#     def _get_base_amount(self):
#         for invoice_tax in self:
#             # search for invoice lines of this tax and invoice
#             invoice_lines = self.env['account.invoice.line'].search([
#                 ('invoice_id', '=', invoice_tax.invoice_id.id),
#                 ('invoice_line_tax_ids', '=', invoice_tax.tax_id.id),
#             ])
#             invoice_tax.base_amount = sum(
#                 invoice_lines.mapped('price_subtotal'))
