# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class account_journal_document_config(osv.osv_memory):

    _name = 'account.journal.document_config'

    _columns = {
        'debit_notes': fields.selection([('dont_use','Do not use'),('own_sequence','Own Sequence'),('same_sequence','Same Invoice Sequence')], string='Debit Notes', required=True,),
        'credit_notes': fields.selection([('own_sequence','Own Sequence'),('same_sequence','Same Invoice Sequence')], string='Credit Notes', required=True,),
    }
