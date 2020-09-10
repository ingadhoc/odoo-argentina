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
