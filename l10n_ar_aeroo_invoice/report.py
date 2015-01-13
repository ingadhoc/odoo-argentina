# -*- coding: utf-8 -*-
from openerp import models, fields


class ir_actions_report(models.Model):
    _inherit = 'ir.actions.report.xml'

    afip_document_class_ids = fields.Many2many(
        'afip.document_class', 'repot_afip_document_class_rel',
        'report_id', 'document_class_id',
        string='Document Types',
        )

    def get_domains(self, cr, model, record, context=None):
        domains = super(ir_actions_report, self).get_domains(
            cr, model, record, context=context)
        new_domains = []
        if model == 'account.invoice':
            account_invoice_state = False

            # We user ignore_state to get the report to split invoice before
            # the invoice is validated
            ignore_state = context.get('ignore_state', False)
            if ignore_state:
                account_invoice_state = ['approved_invoice', 'proforma', False]
            elif record.state in ['proforma', 'proforma2']:
                account_invoice_state = ['proforma']
            elif record.state in ['open', 'paid', 'sale']:
                account_invoice_state = ['approved_invoice']
            # Search for especific document type and journal report
            new_domains.append([('account_invoice_state', 'in', account_invoice_state),
                            ('account_invoice_journal_ids', '=', record.journal_id.id),
                            ('afip_document_class_ids', '=', record.afip_document_class_id.id)])
            # Search for especific document type without journal report
            new_domains.append([('account_invoice_state', 'in', account_invoice_state),
                            ('account_invoice_journal_ids', '=', False),
                            ('afip_document_class_ids', '=', record.afip_document_class_id.id)])
            # Search for especific document type without journal report and without state
            new_domains.append([('account_invoice_state', '=', False),
                            ('account_invoice_journal_ids', '=', False),
                            ('afip_document_class_ids', '=', record.afip_document_class_id.id)])
        return new_domains + domains
