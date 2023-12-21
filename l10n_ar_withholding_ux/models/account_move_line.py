##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
# import odoo.addons.decimal_precision as dp
# from odoo.exceptions import ValidationError
# from dateutil.relativedelta import relativedelta
# import datetime


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # TODO ver si lo podemos borrar
    automatic = fields.Boolean(
    )
    withholding_sequence_id = fields.Many2one(related='tax_line_id.l10n_ar_withholding_sequence_id')

    withholding_accumulated_payments = fields.Selection(
        related='tax_line_id.withholding_accumulated_payments',
    )
    base_amount = fields.Monetary(compute='_compute_base_amount', readonly=False)
    tax_id = fields.Many2one('account.tax', compute='_compute_tax_id', readonly=False)
    # TODO todo esto deberia ir a un json
    # de hecho podemos revisar y lo que no necesitemos consultar para operar, podemos guardarlo en un memo, chatter o similar
    withholdable_invoiced_amount = fields.Float('Importe imputado sujeto a retencion', readonly=True,)
    withholdable_advanced_amount = fields.Float('Importe a cuenta sujeto a retencion',)
    accumulated_amount = fields.Float(readonly=True,)
    total_amount = fields.Float(readonly=True,)
    withholding_non_taxable_minimum = fields.Float('Non-taxable Minimum', readonly=True,)
    withholding_non_taxable_amount = fields.Float('Non-taxable Amount', readonly=True,)
    withholdable_base_amount = fields.Float(readonly=True,)
    period_withholding_amount = fields.Float(readonly=True,)
    previous_withholding_amount = fields.Float(readonly=True,)
    computed_withholding_amount = fields.Float(readonly=True,)

    def _compute_tax_id(self):
        for rec in self:
            rec.tax_id = rec.tax_line_id

    @api.depends('tax_id')
    def _compute_base_amount(self):
        for rec in self:
            rec.base_amount = abs(sum(rec.move_id.line_ids.filtered(lambda x: rec.tax_line_id.id in x.tax_ids.ids).mapped('amount_currency')))

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
        tax_repartition_line_id = taxes_res['taxes'][0]['tax_repartition_line_id']
        # return tax_amount, tax_account_id, tax_repartition_line_id
        return tax_account_id, tax_repartition_line_id
