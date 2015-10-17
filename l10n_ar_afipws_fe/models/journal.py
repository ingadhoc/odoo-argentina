# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api
import logging
_logger = logging.getLogger(__name__)


class account_journal(models.Model):
    _inherit = 'account.journal'

    @api.multi
    def get_journal_letter(self):
        """Function to be inherited by afip ws fe"""
        letters = super(account_journal, self).get_journal_letter()
        # filter only for sales journals

        if self.type not in ['sale', 'sale_refund']:
            return letters
        if self.point_of_sale_id.afip_ws == 'wsfe':
            letters = letters.filtered(
                lambda r: r.name != 'E')
        elif self.point_of_sale_id.afip_ws == 'wsfex':
            letters = letters.filtered(
                lambda r: r.name == 'E')
        return letters
