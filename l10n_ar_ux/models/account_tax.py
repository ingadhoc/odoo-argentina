##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    jurisdiction_code = fields.Char(compute='_compute_jurisdiction_code')

    @api.depends()
    def _compute_jurisdiction_code(self):
        for rec in self:
            tag = rec.invoice_repartition_line_ids.tag_ids.filtered('jurisdiction_code')
            rec.jurisdiction_code = tag[0].jurisdiction_code if tag else False

    def compute_all(self, price_unit, currency=None, quantity=1, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, fixed_multiplicator=1):
        self.env.context = dict(self.env.context, round=True)
        return super().compute_all(price_unit, currency, quantity, product, partner, is_refund, handle_price_include, include_caba_tags, fixed_multiplicator)
