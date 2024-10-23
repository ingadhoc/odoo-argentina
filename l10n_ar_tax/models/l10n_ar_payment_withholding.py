from odoo import models, fields
from odoo.exceptions import UserError


class l10nArPaymentRegisterWithholding(models.Model):
    _name = 'l10n_ar.payment.withholding'
    _description = 'Payment withholding lines'

    payment_id = fields.Many2one('account.payment', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='payment_id.company_id')
    currency_id = fields.Many2one(related='payment_id.company_currency_id')
    name = fields.Char(string='Number')
    ref = fields.Char()
    tax_id = fields.Many2one('account.tax', check_company=True, required=True)
    withholding_sequence_id = fields.Many2one(related='tax_id.l10n_ar_withholding_sequence_id')
    # base_amount = fields.Monetary(compute='_compute_base_amount', store=True, readonly=False,
    #                               required=True)
    base_amount = fields.Monetary(required=True)
    # por ahora dejamos amount a mano como era antes y que solo se compute con el compute withholdings desde arriba
    # luego vemos de hacer que toda la logica este acá
    amount = fields.Monetary(required=True)
    # amount = fields.Monetary(required=True, compute='_compute_amount', store=True, readonly=False)

    # TODO ver como podemos unificar o abstraer código en modelo abstract y re utilizar acá y en aml
    automatic = fields.Boolean()
    withholding_accumulated_payments = fields.Selection(related='tax_id.withholding_accumulated_payments',)
    withholdable_invoiced_amount = fields.Monetary('Importe imputado sujeto a retencion', readonly=True,)
    withholdable_advanced_amount = fields.Monetary('Importe a cuenta sujeto a retencion',)
    accumulated_amount = fields.Monetary(readonly=True,)
    total_amount = fields.Monetary(readonly=True,)
    withholding_non_taxable_minimum = fields.Monetary('Non-taxable Minimum', readonly=True,)
    withholding_non_taxable_amount = fields.Monetary('Non-taxable Amount', readonly=True,)
    withholdable_base_amount = fields.Monetary(readonly=True,)
    period_withholding_amount = fields.Monetary(readonly=True,)
    previous_withholding_amount = fields.Monetary(readonly=True,)
    computed_withholding_amount = fields.Monetary(readonly=True,)

    _sql_constraints = [('uniq_line', 'unique(tax_id, payment_id)', "El impuesto de retención debe ser único por pago")]

    # def _compute_base_amount(self):

    def _tax_compute_all_helper(self):
        self.ensure_one()
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100
        taxes_res = self.tax_id.compute_all(
            self.base_amount,
            currency=self.payment_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        # tax_amount = taxes_res['taxes'][0]['amount']
        tax_account_id = taxes_res['taxes'][0]['account_id']
        if not tax_account_id:
            raise UserError(
                'El impuesto "%s" no tiene configurada una cuenta en la linea de reparticion.' % self.tax_id.name)
        tax_repartition_line_id = taxes_res['taxes'][0]['tax_repartition_line_id']
        # return tax_amount, tax_account_id, tax_repartition_line_id
        return tax_account_id, tax_repartition_line_id

    # @api.depends('tax_id', 'base_amount')
    # def _compute_amount(self):
    #     for line in self:
    #         if not line.tax_id:
    #             line.amount = 0.0
    #         else:
    #             line.amount, dummy, dummy = line._tax_compute_all_helper()

    # @api.depends('tax_id', 'payment_id.line_ids', 'payment_id.amount', 'payment_id.currency_id')
    # def _compute_base_amount(self):
    #     supplier_recs = self.filtered(lambda x: x.payment_id.partner_type == 'supplier')
    #     base_lines = self.payment_register_id.line_ids.move_id.invoice_line_ids.filtered(lambda x: x.display_type == 'product')
    #     for rec in supplier_recs:
    #         factor = rec.payment_register_id._l10n_ar_get_payment_factor()
    #         if not rec.tax_id:
    #             rec.base_amount = 0.0
    #             continue
    #         base_amount = rec._get_base_amount(base_lines, factor)
    #         if base_amount:
    #             rec.base_amount = base_amount
    #     # Only supplier compute base tax
    #     (self - supplier_recs).base_amount = 0.0

    # def _get_base_amount(self, base_lines, factor):
    #     conversion_rate = self.payment_register_id._get_conversion_rate()
    #     tax_base_lines = base_lines.filtered(lambda x: self.tax_id in x.product_id.l10n_ar_supplier_withholding_taxes_ids)
    #     if self.tax_id.l10n_ar_withholding_amount_type == 'untaxed_amount':
    #         base_amount = factor * sum(tax_base_lines.mapped('price_subtotal'))
    #     else:
    #         base_amount = factor * sum(tax_base_lines.mapped('price_total'))
    #     return self.payment_register_id.currency_id.round(base_amount / conversion_rate)
