##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # for performance (should be a PR to odoo)
    tax_group_id = fields.Many2one(
        auto_join=True,
    )
    amount_untaxed = fields.Float(
        string='Untaxed',
        compute='_compute_amounts',
    )
    amount_tax = fields.Float(
        string='Tax',
        compute='_compute_amounts',
    )
    amount_total = fields.Float(
        string='Total',
        compute='_compute_amounts',
    )

    @api.multi
    def _compute_amounts(self):
        vat_ledger_id = self._context.get('vat_ledger_id', False)
        if not vat_ledger_id:
            return
        vat_ledger = self.env['account.vat.ledger'].browse(vat_ledger_id)
        for rec in self:
            (amount_untaxed, amount_tax, amount_total) = rec.get_amounts(
                vat_ledger)
            rec.amount_untaxed = amount_untaxed
            rec.amount_tax = amount_tax
            rec.amount_total = amount_total

    @api.model
    def get_amounts(
            self, vat_ledger, responsability=False, invoice_type=None):
        taxes_domain = [
            ('invoice_id', 'in', vat_ledger.invoice_ids.ids),
            ('invoice_id.state', '!=', 'cancel'),
            ('tax_id.id', '=', self.id)]
        if invoice_type:
            taxes_domain.append(
                ('invoice_id.type', 'in', invoice_type))
        if responsability:
            taxes_domain.append(
                ('invoice_id.afip_responsability_type_id',
                    '=', responsability.id))
        # invoice_taxes = self.env['account.invoice.tax'].search(
        #     taxes_domain)
        invoice_taxes = self.env['account.invoice.tax'].search(
            taxes_domain +
            [('invoice_id.type', 'in', ['in_invoice', 'out_invoice'])])
        refund_invoice_taxes = self.env['account.invoice.tax'].search(
            taxes_domain +
            [('invoice_id.type', 'in', ['in_refund', 'out_refund'])])
        amount_untaxed = (
            sum(invoice_taxes.mapped('cc_base')) -
            sum(refund_invoice_taxes.mapped('cc_base')))
        amount_tax = (
            sum(invoice_taxes.mapped('cc_amount')) -
            sum(refund_invoice_taxes.mapped('cc_amount')))
        amount_total = amount_untaxed + amount_tax
        return (amount_untaxed, amount_tax, amount_total)
