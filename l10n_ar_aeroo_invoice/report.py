# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
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

            # TODO we should improove this

            # We use ignore_state to get the report to split invoice before
            # the invoice is validated
            ignore_state = context.get('ignore_state', False)
            if ignore_state:
                account_invoice_state = ['approved_invoice', 'proforma', False]
            elif record.state in ['proforma', 'proforma2']:
                account_invoice_state = ['proforma']
            elif record.state in ['open', 'paid', 'sale']:
                account_invoice_state = ['approved_invoice']
            # Search for especific state and document type and journal
            new_domains.append([
                ('account_invoice_state', 'in', account_invoice_state),
                ('account_invoice_journal_ids', '=', record.journal_id.id),
                ('afip_document_class_ids', '=',
                    record.afip_document_class_id.id)])

            # Search for especific state and document type without journal
            new_domains.append([
                ('account_invoice_state', 'in', account_invoice_state),
                ('account_invoice_journal_ids', '=', False),
                ('afip_document_class_ids', '=',
                    record.afip_document_class_id.id)])

            # Search for especific state and journal without document type
            new_domains.append([
                ('account_invoice_state', 'in', account_invoice_state),
                ('account_invoice_journal_ids', '=', record.journal_id.id),
                ('afip_document_class_ids', '=', False)])

            # Search for especific document type and journal without state
            new_domains.append([
                ('account_invoice_state', 'in', False),
                ('account_invoice_journal_ids', '=', record.journal_id.id),
                ('afip_document_class_ids', '=',
                    record.afip_document_class_id.id)])

            # Search for especific document type without state and journal
            new_domains.append([
                ('account_invoice_state', 'in', False),
                ('account_invoice_journal_ids', '=', False),
                ('afip_document_class_ids', '=',
                    record.afip_document_class_id.id)])

            # Search for especific journal without state and document type
            new_domains.append([
                ('account_invoice_state', 'in', False),
                ('account_invoice_journal_ids', '=', record.journal_id.id),
                ('afip_document_class_ids', '=', False)])

            # Search for especific document type without journal and
            # without state
            new_domains.append([
                ('account_invoice_state', '=', False),
                ('account_invoice_journal_ids', '=', False),
                ('afip_document_class_ids', '=',
                    record.afip_document_class_id.id)])
        return new_domains + domains
