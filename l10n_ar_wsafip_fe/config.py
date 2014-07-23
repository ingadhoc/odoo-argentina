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
import base64
from M2Crypto import X509

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

class l10n_ar_wsafip_fe_config(osv.osv_memory):
    def _default_company(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id

    def update_data(self, cr, uid, ids, company_id, context=None):
        journal_obj = self.pool.get('account.journal')
        v = { 'journal_ids': journal_obj.search(cr, uid, [('company_id','=',company_id),
                                                          ('journal_class_id','!=',False)]) }
        return {'value': v}

    def _get_journals(self, cr, uid, ids, field_name, arg, context=None):
        journal_obj = self.pool.get('account.journal')
        result = dict( (id, self.items) for id in ids )
        return result

    def _get_pos(self, cr, uid, context=None):
        cr.execute("""
                  SELECT point_of_sale
                  FROM account_journal
                  WHERE point_of_sale is not Null
                  GROUP BY point_of_sale
                  ORDER BY point_of_sale
                  """)
        items = [ ("%i" % i, _("Point of sale %i") % i) for i in cr.fetchall() ]
        return items

    def _set_journals(self, cr, uid, ids, field_name, field_value, fnct_inv_arg, context=None):
        journal_obj = self.pool.get('account.journal')
        self.items = field_value[0][2]
        return True

    def execute(self, cr, uid, ids, context=None):
        """
        """
        conn_obj = self.pool.get('wsafip.connection')
        journal_obj = self.pool.get('account.journal')
        afipserver_obj = self.pool.get('wsafip.server')
        sequence_obj = self.pool.get('ir.sequence')

        for ws in self.browse(cr, uid, ids):
            # Tomamos la compania
            company = ws.company_id
            conn_class = 'homologation' if ws.wsfe_for_homologation else 'production'

            # Hay que crear la autorizacion para el servicio si no existe.
            conn_ids = conn_obj.search(cr, uid, [('partner_id','=',company.partner_id.id)])

            if len(conn_ids) == 0:
                # Hay que crear la secuencia de proceso en batch si no existe.
                seq_ids = sequence_obj.search(cr, uid, [('code','=','wsafip_fe_sequence')])
                if seq_ids:
                    seq_id = seq_ids[0]
                else:
                    seq_id = sequence_obj.create(cr, uid, {'name': 'Web Service AFIP Sequence for Invoices', 'code': 'ws_afip_sequence'})

                # Crear el conector al AFIP
                conn_id = conn_obj.create(cr, uid, {
                    'name': 'AFIP Sequence Authorization Invoice: %s' % company.name,
                    'partner_id': company.partner_id.id,
                    'logging_id': afipserver_obj.search(cr, uid, [('code','=','wsaa'),('class','=',conn_class)])[0],
                    'server_id': afipserver_obj.search(cr, uid, [('code','=','wsfe'),('class','=',conn_class)])[0],
                    'certificate': ws.wsfe_certificate_id.id,
                    'batch_sequence_id': seq_id,
                })
            else:
                conn_id = conn_ids[0]

            # Asigno el conector al AFIP
            jou_ids = journal_obj.search(cr, uid, [('company_id','=',company.id),
                                                   ('point_of_sale','=',ws.wsfe_point_of_sale),
                                                   ('type','=','sale')])

            journal_obj.write(cr, uid, jou_ids, { 'afip_connection_id': conn_id })

            # Sincronizo el número de factura local con el remoto
            for journal in journal_obj.browse(cr, uid, jou_ids):
                remote_number = journal.afip_items_generated
                seq_id = journal.sequence_id.id
                if not type(remote_number) is bool:
                    _logger.info("Journal '%s' syncronized." % journal.name)
                    sequence_obj.write(cr, uid, seq_id, {'number_next': remote_number + 1})
                else:
                    _logger.info("Journal '%s' cant be used." % journal.name)

            # Actualizo el código de impuestos de la AFIP en los impuestos locale.s
            conn = conn_obj.browse(cr, uid, conn_id)
            conn.server_id.wsfe_update_tax(conn_id)
            
        return True

    _name = 'l10n_ar_wsafip_fe.config'
    _inherit = 'res.config'
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'wsfe_certificate_id': fields.many2one('crypto.certificate', 'Certificate', required=True),
        'wsfe_for_homologation': fields.boolean('Is for homologation'),
        'wsfe_point_of_sale': fields.selection(_get_pos, 'Point of Sale', required=True),
    }
    _defaults= {
        'company_id': _default_company,
        'wsfe_for_homologation': False,
    }
l10n_ar_wsafip_fe_config()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
