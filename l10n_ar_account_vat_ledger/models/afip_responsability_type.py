from odoo import models, fields, api


class AfipResponsabilityType(models.Model):
    _inherit = 'afip.responsability.type'

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
    def get_amounts(self, vat_ledger, tax_code=False):
        domain = [
            ('state', 'not in', ['draft', 'cancel']),
            ('afip_responsability_type_id', '=', self.id),
            ('id', 'in', vat_ledger.invoice_ids.ids),
        ]
        invoices = self.env['account.invoice'].search(
            domain + [('type', 'in', ['in_invoice', 'out_invoice'])])
        refund_invoices = self.env['account.invoice'].search(
            domain + [('type', 'in', ['in_refund', 'out_refund'])])
        amount_untaxed = sum(invoices.mapped('cc_amount_untaxed')) - sum(
            refund_invoices.mapped('cc_amount_untaxed'))
        amount_tax = sum(invoices.mapped('cc_amount_tax')) - sum(
            refund_invoices.mapped('cc_amount_tax'))
        amount_total = sum(invoices.mapped('cc_amount_total')) - sum(
            refund_invoices.mapped('cc_amount_total'))
        return (amount_untaxed, amount_tax, amount_total)
