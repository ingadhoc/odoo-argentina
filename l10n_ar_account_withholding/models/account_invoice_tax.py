# -*- coding: utf-8 -*-
from openerp import models, api, fields
import logging
_logger = logging.getLogger(__name__)


class account_invoice_tax(models.Model):
    _inherit = "account.invoice.tax"

    @api.v8
    def compute(self, invoice):
        date_invoice = invoice.date_invoice or fields.Date.context_today(
            invoice)
        invoice = invoice.with_context(
            invoice_date=date_invoice,
            invoice_company=invoice.company_id)
        return super(account_invoice_tax, self).compute(invoice)
