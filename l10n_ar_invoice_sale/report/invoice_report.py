# -*- coding: utf-8 -*-
from openerp import models, fields


class account_invoice_report(models.Model):
    _inherit = 'account.invoice.report'

    afip_document_class_id = fields.Many2one(
        'afip.document_class',
        string='Document Type',
        )

    _depends = {
        'account.invoice': ['afip_document_class_id'],
    }

    def _select(self):
        return super(
            account_invoice_report, self)._select() + ", sub.afip_document_class_id as afip_document_class_id"

    def _sub_select(self):
        return super(
            account_invoice_report, self)._sub_select() + ", ai.afip_document_class_id as afip_document_class_id"

    def _group_by(self):
        return super(account_invoice_report, self)._group_by() + ", ai.afip_document_class_id"
