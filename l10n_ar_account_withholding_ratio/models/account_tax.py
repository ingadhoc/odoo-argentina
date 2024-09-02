from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    ratio = fields.Float(default=100.00, help="Ratio to apply to tax base amount.")

    @api.constrains('ratio')
    def _check_line_ids_percent(self):
        """ Check that the total percent is not bigger than 100.0 """
        for tax in self:
            if not tax.ratio or tax.ratio < 0.0 or tax.ratio > 100.0:
                raise ValidationError(_('The total percentage (%s) should be higher than 0 and less or equal to 100.', tax.ratio))

    def get_withholding_vals(self, payment):
        vals = super().get_withholding_vals(payment)
        if self.withholding_type == 'partner_tax' and self.ratio != 100:
            vals['withholdable_base_amount'] *= self.ratio / 100
            vals['period_withholding_amount'] *= self.ratio / 100
        return vals

    def _compute_amount(
            self, base_amount, price_unit, quantity, product, partner=None, fixed_multiplicator=1):
        if self.amount_type == 'partner_tax' and self.ratio != 100:
            date = self._context.get('invoice_date') or fields.Date.context_today(self)
            partner = partner and partner.sudo()
            return base_amount * self.sudo().get_partner_alicuota_percepcion(partner, date) * self.ratio / 100
        return super()._compute_amount(base_amount, price_unit, quantity, product, partner=partner, fixed_multiplicator=fixed_multiplicator)
