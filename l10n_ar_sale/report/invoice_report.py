# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class account_invoice_report(models.Model):
    _inherit = 'account.invoice.report'

    document_type_id = fields.Many2one(
        'account.document.type',
        string='Document Type',
        )

    _depends = {
        'account.invoice': ['document_type_id'],
    }

    def _select(self):
        return super(
            account_invoice_report, self)._select() + ", sub.document_type_id as document_type_id"

    def _sub_select(self):
        return super(
            account_invoice_report, self)._sub_select() + ", ai.document_type_id as document_type_id"

    def _group_by(self):
        return super(account_invoice_report, self)._group_by() + ", ai.document_type_id"
