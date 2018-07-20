##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class AcountDocumentType(models.Model):
    _inherit = 'account.document.type'

    amount_untaxed = fields.Monetary(
        string='Untaxed',
        compute='_compute_amounts',
    )
    other_taxes_amount = fields.Monetary(
        compute="_compute_amounts",
        string='Other Taxes Amount'
    )
    vat_amount = fields.Monetary(
        compute="_compute_amounts",
        string='VAT Amount'
    )
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
    )
    currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_amounts'
    )

    @api.multi
    def _compute_amounts(self):
        """
        """
        vat_ledger_id = self._context.get('vat_ledger_id', False)
        if not vat_ledger_id:
            return
        vat_ledger = self.env['account.vat.ledger'].browse(vat_ledger_id)
        for rec in self:
            (
                amount_untaxed, vat_amount,
                other_taxes_amount, amount_total
            ) = rec.get_amounts(vat_ledger)
            rec.currency_id = vat_ledger.company_id.currency_id
            rec.amount_untaxed = amount_untaxed
            rec.vat_amount = vat_amount
            rec.other_taxes_amount = other_taxes_amount
            rec.amount_total = amount_total

    @api.model
    def get_amounts(self, vat_ledger):
        domain = [
            ('state', 'not in', ['draft', 'cancel']),
            ('document_type_id', '=', self.id),
            ('id', 'in', vat_ledger.invoice_ids.ids),
        ]
        invoices = self.env['account.invoice'].search(domain)
        amount_untaxed = sum(invoices.mapped('cc_amount_untaxed'))
        vat_amount = sum(invoices.mapped('cc_vat_amount'))
        other_taxes_amount = sum(invoices.mapped('cc_other_taxes_amount'))
        amount_total = sum(invoices.mapped('cc_amount_total'))
        if self.internal_type == 'credit_note':
            amount_untaxed = -amount_untaxed
            vat_amount = -vat_amount
            other_taxes_amount = -other_taxes_amount
            amount_total = -amount_total
        return (amount_untaxed, vat_amount, other_taxes_amount, amount_total)
