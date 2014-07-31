# -*- coding: utf-8 -*-
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class account_journal_document_config(osv.osv_memory):

    _name = 'account.journal.document_config'

    _columns = {
        'debit_notes': fields.selection([('dont_use','Do not use'),('own_sequence','Own Sequence'),('same_sequence','Same Invoice Sequence')], string='Debit Notes', required=True,),
        'credit_notes': fields.selection([('own_sequence','Own Sequence'),('same_sequence','Same Invoice Sequence')], string='Credit Notes', required=True,),
    }

    _defaults= {
        'debit_notes': 'own_sequence',
        'credit_notes': 'own_sequence',
    }

    def confirm(self, cr, uid, ids, context=None):
        """
        Confirm Configure button
        """
        if context is None:
            context = {}

        journal_ids = context.get('active_ids', False)
        wizard = self.browse(cr, uid, ids[0], context=context)
        self.create_journals(cr, uid, wizard.debit_notes, wizard.credit_notes, journal_ids, context=context)

    def create_journals(self, cr, uid, debit_notes, credit_notes, journal_ids, context=None):
      print 'sdas', debit_notes, credit_notes, journal_ids, context
      for journal in self.pool['account.journal'].browse(cr, uid, journal_ids, context=context):
        responsability = journal.company_id.responsability_id
        if not responsability.id:
            raise orm.except_orm(_('Your company has not setted any responsability'),
                    _('Please, set your company responsability in the company partner before continue.'))            
            _logger.warning('Your company "%s" has not setted any responsability.' % journal.company_id.name)
      
        journal_type = journal.type
        if journal_type in ['sale', 'sale_refund']:
          letter_ids = [x.id for x in responsability.issued_letter_ids]
        elif journal_type in ['purchase', 'purchase_refund']:
          letter_ids = [x.id for x in responsability.received_letter_ids]
        
        if journal_type == 'sale':
          document_type = 'invoice'            
          self.create_journal_document(cr, uid, letter_ids, document_type, journal.id, credit_notes, debit_notes, context)
          # Create sale debit notes
          if debit_notes != 'dont_use':
            document_type = 'debit_note'            
            self.create_journal_document(cr, uid, letter_ids, document_type, journal.id, credit_notes, debit_notes, context)
        elif journal_type == 'sale_refund':
          # Create sale credit notes
            document_type = 'credit_note'            
            self.create_journal_document(cr, uid, letter_ids, document_type, journal.id, credit_notes, debit_notes, context)
        elif journal_type == 'purchase':
          document_type = 'invoice'
          self.create_journal_document(cr, uid, letter_ids, document_type, journal.id, credit_notes, debit_notes, context)
          document_type = 'debit_note'            
          self.create_journal_document(cr, uid, letter_ids, document_type, journal.id, credit_notes, debit_notes, context)            
        elif journal_type == 'purchase_refund':
          document_type = 'credit_note'
          self.create_journal_document(cr, uid, letter_ids, document_type, journal.id, credit_notes, debit_notes, context)

    def create_sequence(self, cr, uid, name, journal, context=None):
      vals = {
        'name': journal.name + ' - ' + name,
        'padding': 8,
        'prefix': "%04i-" % (journal.point_of_sale),
      }
      sequence_id = self.pool['ir.sequence'].create(cr, uid, vals, context=context)
      return sequence_id

    def create_journal_document(self, cr, uid, letter_ids, document_type, journal_id, credit_notes, debit_notes, context=None):
      print letter_ids, document_type, journal_id, credit_notes, debit_notes
      document_class_obj = self.pool['afip.document_class']
      document_class_ids = document_class_obj.search(cr, uid, [('document_letter_id', 'in', letter_ids),('document_type', '=', document_type)], context=context)
      journal_document_obj = self.pool['account.journal.afip_document_class']
      journal = self.pool['account.journal'].browse(cr, uid, journal_id, context=context)
      sequence = 10
      for document_class in document_class_obj.browse(cr, uid, document_class_ids, context=context):
        sequence_id = False
        if journal.type == 'sale':
          if document_type == 'invoice' or document_type == 'debit_note' and debit_notes == 'own_sequence':
            sequence_id = self.create_sequence(cr, uid, document_class.name, journal, context)
          elif document_type == 'debit_note' and debit_notes == 'same_sequence':
            domain = [('afip_document_class_id.document_letter_id','=',document_class.document_letter_id.id),
              ('journal_id.point_of_sale','=',journal.point_of_sale)]
            journal_docuent_ids = journal_document_obj.search(cr, uid, [('afip_document_class_id.document_letter_id','=',document_class.document_letter_id.id),
              ('journal_id.point_of_sale','=',False)], context=context)
            if not journal_docuent_ids:
              journal_docuent_ids = journal_document_obj.search(cr, uid, domain, context=context)
            if journal_docuent_ids:
              sequence_id = journal_document_obj.browse(cr, uid, journal_docuent_ids[0], context=context).sequence_id.id
        elif journal.type == 'sale_refund':
          if credit_notes == 'own_sequence':
            sequence_id = self.create_sequence(cr, uid, document_class.name, journal, context)
          elif credit_notes == 'same_sequence':
            domain = [('afip_document_class_id.document_letter_id','=',document_class.document_letter_id.id),
              ('journal_id.point_of_sale','=',journal.point_of_sale)]
            journal_docuent_ids = journal_document_obj.search(cr, uid, domain, context=context)
            if journal_docuent_ids:
              sequence_id = journal_document_obj.browse(cr, uid, journal_docuent_ids[0], context=context).sequence_id.id
        vals = {
          'afip_document_class_id': document_class.id,
          'sequence_id': sequence_id,
          'journal_id': journal.id,
          'sequence': sequence,
        }
        journal_document_obj.create(cr, uid, vals, context=context)
        sequence +=10