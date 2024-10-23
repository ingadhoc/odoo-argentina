from odoo import fields, models, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    ratio = fields.Float(required=True, default=100, help="Ratio to apply to tax base amount")

    @api.constrains('ratio')
    def _check_line_ids_percent(self):
        """ Check that the total percent is not bigger than 100.0 """
        for tax in self:
            if not (0 < tax.ratio <= 100.0):
                raise ValidationError(_('The total percentage (%s) should be less or equal to 100!', tax.ratio))

    def create_payment_withholdings(self, payment_group):
        for tax in self.filtered(lambda x: x.withholding_type != 'none'):
            super().create_payment_withholdings(payment_group)
            payment_withholding = self.env['account.payment'].search([
                ('payment_group_id', '=', payment_group.id),
                ('tax_withholding_id', '=', tax.id),
                ('automatic', '=', True),
            ], limit=1)
            if payment_withholding:
                vals = tax.get_withholding_vals(payment_group)
                vals['withholding_base_amount'] = (vals.get('withholdable_advanced_amount') + vals.get('withholdable_invoiced_amount')) * tax.ratio / 100
                payment_withholding.write({'withholding_base_amount': vals['withholding_base_amount']})

    def get_withholding_vals(self, payment_group):
        vals = super().get_withholding_vals(payment_group)
        if self.withholding_type == 'partner_tax' and self.ratio:
            vals['withholdable_base_amount'] *= self.ratio / 100
            vals['period_withholding_amount'] *= self.ratio / 100
        return vals

    def _compute_amount(
            self, base_amount, price_unit, quantity, product, partner=None, fixed_multiplicator=1):
        super()._compute_amount(base_amount, price_unit, quantity, product, partner=partner, fixed_multiplicator=fixed_multiplicator)
        if self.amount_type == 'partner_tax':
            date = self._context.get('invoice_date', fields.Date.context_today(self))

            if not date:
                date = fields.Date.context_today(self)
            partner = partner and partner.sudo()
            return base_amount * self.sudo().get_partner_alicuota_percepcion(partner, date) * self.ratio / 100
