# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _
from openerp.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    @api.multi
    @api.constrains('manual', 'tax_id')
    def check_vat_not_manual(self):
        for rec in self:
            if rec.manual and rec.tax_id.tax_group_id.type == 'tax' and \
                    rec.tax_id.tax_group_id.tax == 'vat':
                raise ValidationError(_(
                    'No puede agregar IVA manualmente, debe agregarlo en las '
                    'líneas de factura.'))
