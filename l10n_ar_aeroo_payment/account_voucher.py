# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp


class account_voucher_line(models.Model):
    _inherit = 'account.voucher.line'

    signed_amount = fields.Float(
        digits=dp.get_precision('Account'),
        compute='_get_signed_amount',
        string=_('Signed Amount'),
    )

    @api.one
    def _get_signed_amount(self):
        if self.voucher_id.type == 'payment':
            if self.type == 'cr':
                # negative for credits
                sign = -1.0
            else:
                # positive for debits
                sign = 1.0
        # for receipts
        else:
            if self.type == 'dr':
                # negative for debits
                sign = -1.0
            else:
                # positive for debits
                sign = 1.0
        self.signed_amount = self.amount * sign
