# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2012 OpenERP - Team de Localización Argentina.
# https://launchpad.net/~openerp-l10n-ar-localization
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class l10n_ar_invoice_config(osv.osv_memory):
    
    def _default_company(self, cr, uid, c, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id

    def _default_responsability(self, cr, uid, c, context=None):
        resp_obj = self.pool.get('afip.responsability')
        ids = resp_obj.search(cr, uid, [('name','=','Responsable Monotributo')])
        return ids.pop()

    _name = 'l10n_ar_invoice.config'

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True),
        'cuit': fields.char('CUIT', size=12, required=True),
        'iibb': fields.char('IIBB', size=12, required=True),
        'start_date': fields.date('Inicio de Actividades', required=True),
        'responsability_id': fields.many2one('afip.responsability', 'Resposability', required=True, domain=[('code','!=','CF')]),
        'update_posted': fields.boolean('Allow Cancelling Entries', help="Check this box if you want to allow the cancellation the entries related to this journals or of the invoice related to this journals"),        
        'group_invoice_lines': fields.boolean('Group Invoice Lines', help="If this box is checked, the system will try to group the accounting lines when generating them from invoices."),
        'allow_date':fields.boolean('Check Date in Period', help= 'If checked, the entry won\'t be created if the entry date is not included into the selected period'),
        'debit_notes': fields.selection([('dont_use','Do not use'),('own_sequence','Own Sequence'),('same_sequence','Same Invoice Sequence')], string='Debit Notes', required=True,),
        'credit_notes': fields.selection([('dont_use','Do not use'),('own_sequence','Own Sequence'),('same_sequence','Same Invoice Sequence')], string='Credit Notes', required=True,),
        'remove_old_journals': fields.boolean('Eliminar los diarios existentes',
            help=u'Si es su primera instalación indique que necesita borrar los diarios existentes. Si agrega un nuevo punto de ventas indique que no va a eliminar los journals. Igual, puede indicar cuales borra y cuales no en el próximo paso.'),
        'point_of_sale': fields.integer(u'Número de Punto de Venta',
            help=u'Este es el número que aparecerá como prefijo del número de la factura. Si solo tiene un solo talonario ese número es 1. Si necesita agregar un nuevo punto de venta debe acceder a opciones Administración/Configuración/Wizards de Configuración/Wizards de Configuración y ejecutar nuevamente el wizard de "Configuración de Facturación".'),
        'other_sale_journal_ids': fields.many2many('afip.document_class', 'other_sale_journal_rel', 'config_id', 'journal_id','Other Sale Journals', domain=[('journal_subtype','=',False)],),
        'other_purchase_journal_ids': fields.many2many('afip.document_class', 'other_purchase_journal_rel', 'config_id', 'journal_id','Other Purchase Journals', domain=[('journal_subtype','=',False)],),
        'journals_to_remove_ids': fields.many2many('account.journal', 'journal_to_remove_rel', 'config_id', 'journal_id', 'Journals to delete'),
    }

    _defaults= {
        'company_id': _default_company,
        'debit_notes': 'own_sequence',
        'credit_notes': 'own_sequence',
        'update_posted': True,
        'group_invoice_lines': True,
        'allow_date': True,
        'remove_old_journals': True,
        'point_of_sale': 1,
        'journals_to_remove_ids': lambda self, cr, uid, c, context=None: self.update_rem_journals(
            cr, uid, [], self._default_company(cr, uid, c, context), context=context),
    }

    def confirm(self, cr, uid, ids, context=None):
        """
        Confirm Configure button
        """
        if context is None:
            context = {}

        obj_partner = self.pool.get('res.partner')
        obj_document_type = self.pool.get('afip.document_type')

        document_type_cuit = obj_document_type.search(cr, uid, [('code','=','CUIT')])[0]

        for wzd in self.browse(cr, uid, ids, context=context):
          partner_id = wzd.company_id.partner_id.id
          obj_partner.write(cr, uid, partner_id,
                                             {'responsability_id': wzd.responsability_id.id,
                                              'document_number': wzd.cuit,
                                              'document_type_id': document_type_cuit,
                                              'iibb': wzd.iibb,
                                              'start_date': wzd.start_date,
                                              'vat': 'ar%s' % wzd.cuit,
                                             })
          obj_partner.check_vat(cr, uid, [partner_id])
          if wzd.remove_old_journals:
            self.delete_journals(cr, uid, wzd, context=context)
          self.create_journals(cr, uid, [x.id for x in wzd.other_sale_journal_ids], wzd, 'sale', 'other_document', context=context)
          self.create_journals(cr, uid, [x.id for x in wzd.other_purchase_journal_ids], wzd, 'purchase', 'other_document', context=context)
          self.create_invoice_journals(cr, uid, wzd, context=context)

    def create_journals(self, cr, uid, document_class_ids, wizard, journal_type, journal_subtype, context=None):
      document_class_obj = self.pool['afip.document_class']
      account_journal_obj = self.pool['account.journal']
      point_of_sale = wizard.point_of_sale
      company_id = wizard.company_id.id

      if journal_type in ['sale','sale_refund']:
        code_sufix = 'V'
      else:
        code_sufix = 'C'

      for document_class in document_class_obj.browse(cr, uid, document_class_ids, context=context):
        code = document_class.code_template or ''
        code += code_sufix
        name = document_class.name

        sequence_id = False
        if wizard.debit_notes == 'same_sequence' and journal_subtype == 'debit_note' or wizard.credit_notes == 'same_sequence' and journal_subtype == 'credit_note':
          invoice_journal_ids = account_journal_obj.search(cr, uid, [('journal_subtype','=','invoice'),('type','=',journal_type),('afip_document_class_id.document_letter_id.id','=',document_class.document_letter_id.id)], context=context)
          if invoice_journal_ids:
            sequence_id = account_journal_obj.browse(cr, uid, invoice_journal_ids[0], context=context).sequence_id.id
        vals = {
          'name': u"%s (%04i-%s)" % (name, point_of_sale, code),
          'code': u"%s%04i" % (code, point_of_sale),
          'afip_document_class_id': document_class.id,
          'company_id': company_id,
          'point_of_sale': point_of_sale,
          'sequence_id': sequence_id,
          'type': journal_type,
          'group_invoice_lines': wizard.group_invoice_lines,
          'update_posted': wizard.update_posted,
          'allow_date': wizard.allow_date,
        }        
        # credit_note doens not exist in selection to simplify to user
        if journal_subtype != 'credit_note':
          vals['journal_subtype'] = journal_subtype
        account_journal_obj.create(cr, uid, vals, context=context)      
      return True

    def create_invoice_journals(self, cr, uid, wizard, context=None):
      if not context:
        context = {}

      document_class_obj = self.pool['afip.document_class']

      issued_letter_ids = [x.id for x in wizard.responsability_id.issued_letter_ids]
      received_letter_ids = [x.id for x in wizard.responsability_id.received_letter_ids]
      
      # Create sale invoices
      journal_type = 'sale'
      journal_subtype = 'invoice'
      document_class_ids = document_class_obj.search(cr, uid, [('document_letter_id', 'in', issued_letter_ids),('journal_subtype', '=', journal_subtype)], context=context)
      self.create_journals(cr, uid, document_class_ids, wizard, journal_type, journal_subtype, context=context)
      
      # Create sale debit notes
      if wizard.debit_notes != 'dont_use':
        journal_subtype = 'debit_note'
        document_class_ids = document_class_obj.search(cr, uid, [('document_letter_id', 'in', issued_letter_ids),('journal_subtype', '=', journal_subtype)], context=context)
        self.create_journals(cr, uid, document_class_ids, wizard, journal_type, journal_subtype, context=context)

      # Create sale creidt notes
      if wizard.credit_notes != 'dont_use':
        journal_type = 'sale_refund'
        journal_subtype = 'credit_note'
        document_class_ids = document_class_obj.search(cr, uid, [('document_letter_id', 'in', issued_letter_ids),('journal_subtype', '=', journal_subtype)], context=context)
        self.create_journals(cr, uid, document_class_ids, wizard, journal_type, journal_subtype, context=context)

      # Create purchase invoices
      journal_type = 'purchase'
      journal_subtype = 'invoice'
      document_class_ids = document_class_obj.search(cr, uid, [('document_letter_id', 'in', received_letter_ids),('journal_subtype', '=', journal_subtype)], context=context)
      self.create_journals(cr, uid, document_class_ids, wizard, journal_type, journal_subtype, context=context)

      # Create sale debit notes
      if wizard.debit_notes != 'dont_use':
        journal_subtype = 'debit_note'
        document_class_ids = document_class_obj.search(cr, uid, [('document_letter_id', 'in', received_letter_ids),('journal_subtype', '=', journal_subtype)], context=context)
        self.create_journals(cr, uid, document_class_ids, wizard, journal_type, journal_subtype, context=context)

      # Create sale creidt notes
      if wizard.credit_notes != 'dont_use':
        journal_type = 'purchase_refund'
        journal_subtype = 'credit_note'
        document_class_ids = document_class_obj.search(cr, uid, [('document_letter_id', 'in', received_letter_ids),('journal_subtype', '=', journal_subtype)], context=context)
        self.create_journals(cr, uid, document_class_ids, wizard, journal_type, journal_subtype, context=context)      
    
    def delete_journals(self, cr, uid, wizard, context=None):
        """
        Delete all journals selected in journals_to_delete.
        """        
        for read in self.read(cr, uid, [wizard.id], ['journals_to_remove_ids']):
          self.pool['account.journal'].unlink(cr, uid, read['journals_to_remove_ids'], context=context)
        return     

    def update_company_id(self, cr, uid, ids, company_id, context=None):
        """
        Set cuit & iibb
        """
        v = {}
        if company_id:
            company_obj = self.pool.get('res.company')
            company = company_obj.browse(cr, uid, company_id)
            v = {
                'cuit': company.partner_id.document_number,
                'iibb': company.partner_id.iibb,
                'start_date': company.partner_id.start_date,
                'responsability_id': company.partner_id.responsability_id.id,
            }
        return { 'value': v }

    def update_rem_journals(self, cr, uid, ids, company_id, context=None):
        """
        Remove Sale Journal, Purchase Journal, Sale Refund Journal, Purchase Refund Journal.
        """
        obj_journal = self.pool.get('account.journal')
        journal_ids = obj_journal.search(cr, uid, [
          ('type','in',['sale','purchase','sale_refund','purchase_refund']),
          ('company_id','=',company_id)])

        remove_journal_ids = []
        
        for journal_id in journal_ids:
          move_ids = self.pool['account.move'].search(cr, uid, [('journal_id','=',journal_id)], context=context)
          invoice_ids = self.pool['account.invoice'].search(cr, uid, [('journal_id','=',journal_id)], context=context)
          if not move_ids and not invoice_ids:
            remove_journal_ids.append(journal_id)

        return remove_journal_ids

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
