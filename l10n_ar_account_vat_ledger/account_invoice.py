# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields
import logging
_logger = logging.getLogger(__name__)


# for performance
# TODO this should be suggested to odoo by a PR
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    invoice_id = fields.Many2one(
        auto_join=True
    )


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    invoice_id = fields.Many2one(
        auto_join=True
    )
