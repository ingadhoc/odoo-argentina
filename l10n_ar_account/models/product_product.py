##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class ProductProduct(models.Model):

    _inherit = 'product.product'

    @api.multi
    def action_invoice_analysis(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice.line.report',
            # 'res_model': 'account.invoice.report',
            'view_mode': 'tree,pivot,graph',
            # 'view_mode': 'tree,graph',
            'view_type': 'form',
            'domain': [('product_id', 'in', self.ids)],
            'context': {
                # 'search_default_current': 1,
                # 'search_default_customer': 1,
                # 'group_by': [],
                # 'group_by_no_leaf': 1,
                # 'search_default_year': 1
            }
            # 'context': {
            #     'search_default_product_id': self.product_variant_ids[0].id},
        }
