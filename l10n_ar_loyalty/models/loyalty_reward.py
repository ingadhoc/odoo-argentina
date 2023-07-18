from odoo import models


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    def _get_discount_product_values(self):
        res = super()._get_discount_product_values()
        uom_afip_bo = self.env.ref('l10n_ar.product_uom_afip_bo').id
        for values in res:
            values.update({
                'uom_id': uom_afip_bo,
                'uom_po_id': uom_afip_bo,
            })
        return res
