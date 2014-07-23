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
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

class query_invoices(osv.osv_memory):
    _name = 'l10n_ar_wsafip_fe.query_invoices'
    _description = 'Query for invoices in AFIP web services'
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'first_invoice_number': fields.integer('First invoice number', required=True),
        'last_invoice_number': fields.integer('Last invoice number', required=True),
        'update_invoices': fields.boolean('Update CAE if invoice exists'),
        'create_invoices': fields.boolean('Create invoice in draft if not exists'),
    }
    _defaults = {
        'first_invoice_number': 1,
        'last_invoice_number': 1,
    }

    def onchange_journal_id(self, cr, uid, ids, first_invoice_number, journal_id):
        journal_obj = self.pool.get('account.journal')
        res = {}

        if journal_id:
            num_items = journal_obj.browse(cr, uid, journal_id).afip_items_generated
            res['value'] = {
                'first_invoice_number': min(first_invoice_number, num_items), 
                'last_invoice_number': num_items,
            }

        return res

    def execute(self, cr, uid, ids, context=None):
        context = context or {}
        invoice_obj = self.pool.get('account.invoice')
        partner_obj = self.pool.get('res.partner')
        document_type_obj = self.pool.get('afip.document_type')

        for qi in self.browse(cr, uid, ids):
            conn = qi.journal_id.afip_connection_id
            serv = qi.journal_id.afip_connection_id.server_id
            number_format = "%s%%0%sd%s" % (qi.journal_id.sequence_id.prefix, qi.journal_id.sequence_id.padding , qi.journal_id.sequence_id.suffix)

            if qi.first_invoice_number > qi.last_invoice_number:
                raise osv.except_osv(_(u'Qrong invoice range numbers'), _('Please, first invoice number must be less than last invoice'))

            def _fch_(s):
                if s and len(s) == 8:
                    return datetime.strptime(s, "%Y%m%d").strftime('%Y-%m-%d %H:%M:%S')
                elif s and len(s) > 8:
                    return datetime.strptime(s, "%Y%m%d%H%M%S").strftime('%Y-%m-%d %H:%M:%S')
                else:
                    return False

            for inv_number in range(qi.first_invoice_number, qi.last_invoice_number+1):
                r = serv.wsfe_query_invoice(conn.id,
                                            qi.journal_id.journal_class_id.afip_code,
                                            inv_number,
                                            qi.journal_id.point_of_sale)

                r = r[serv.id]

                if r['EmisionTipo'] == 'CAE':
                    inv_ids = invoice_obj.search(cr, uid, [
                        ( 'journal_id', '=', qi.journal_id.id),
                        ( 'number', '=', number_format % inv_number),
                    ])

                    if inv_ids and qi.update_invoices:
                        # Update Invoice
                        # TODO: if invoice in draft complete all data.
                        # TODO: if invoice in not draft just complete cae if not set.
                        _logger.debug("Update invoice number: %s" % (number_format % inv_number))
                    elif not inv_ids and qi.create_invoices:
                        partner_id = partner_obj.search(cr, uid, [
                            ('document_type_id.afip_code','=',r['DocTipo']),
                            ('document_number','=',r['DocNro']),
                        ])
                        if partner_id:
                            # Take partner
                            partner_id = partner_id[0]
                        else:
                            # Create partner
                            _logger.debug("Creating partner doc number: %s" % r['DocNro'])
                            document_type_id = document_type_obj.search(cr, uid, [
                                ('afip_code','=',r['DocTipo']),
                            ])
                            assert len(document_type_id) == 1
                            document_type_id = document_type_id[0]
                            partner_id = partner_obj.create(cr, uid, {
                                'name': r['DocNro'],
                                'document_type_id': document_type_id,
                                'document_number': r['DocNro'],
                            })
                        _logger.debug("Creating invoice number: %s" % (number_format % inv_number))
                        partner = partner_obj.browse(cr, uid, partner_id)
                        if not partner.property_account_receivable.id:
                            raise osv.except_osv(_(u'Partner has not set a receivable account'), _('Please, first set the receivable account for %s') % partner.name)

                        inv_id = invoice_obj.create(cr, uid, {
                            'company_id': qi.journal_id.company_id.id,
                            'account_id': partner.property_account_receivable.id,
                            'internal_number': number_format % inv_number,
                            'name': 'Created from AFIP (%s)' % number_format % inv_number,
                            'journal_id': qi.journal_id.id,
                            'partner_id': partner_id,
                            'date_invoice': _fch_(r['CbteFch']),
                            'afip_cae': r['CodAutorizacion'],
                            'afip_cae_due': _fch_(r['FchProceso']),
                            'afip_service_start': _fch_(r['FchServDesde']),
                            'afip_service_end': _fch_(r['FchServHasta']),
                            'amount_total': r['ImpTotal'],
                            'state': 'draft',
                        })
                    else:
                        _logger.debug("Ignoring invoice: %s" % (number_format % inv_number))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
