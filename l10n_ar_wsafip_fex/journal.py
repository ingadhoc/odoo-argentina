# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2013 Elepe Servicios (http://www.elepeservicios.com.ar)
# All Rights Reserved
#
# Author : Dario Kevin De Giacomo (Elepe Servicios)
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
import urllib2

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

class account_journal(osv.osv):


    def _get_fex_afip_state(self, cr, uid, ids, fields_name, arg, context=None):

        if context is None:
            context={}
        r={}
        for journal in self.browse(cr, uid, ids):
            conn = journal.afip_connection_id
            if not conn:
                r[journal.id] = 'not available'
            elif conn.server_id.code != 'wsfex':
                r[journal.id] = 'connection_service_error'
            else:
                # Try to login just one time.
                try:
                    conn.login()
                    if conn.state not in  [ 'connected', 'clockshifted' ]:
                        r[journal.id] = 'connection_error'
                    else:
                        authserver, appserver, dbserver = conn.server_id.wsfex_get_status(conn.id)[conn.server_id.id]
                        if authserver == 'OK':
                            r[journal.id] = 'connected'
                        else:
                            if appserver != 'OK':
                                r[journal.id] = 'connected_but_appserver_error'
                            elif dbserver != 'OK':
                                r[journal.id] = 'connected_but_dbserver_error'
                            else:
                                r[journal.id] = 'connected_but_servers_error'
                except urllib2.URLError as e:
                    if e[0][0] == 101:
                        r[journal.id] = 'network_down'
                    if e[0][0] == 104:
                        r[journal.id] = 'connection_rejected'
                    elif e[0][0] == -2:
                        r[journal.id] = 'unknown_service'
                    else:
                        r[journal.id] = 'something_wrong'
                except Exception as e:
                    r[journal.id] = 'something_wrong'
                _logger.debug("Connection return: %s" % r[journal.id])
        return r

    def _get_fex_afip_items_generated(self, cr, uid, ids, fields_name, arg, context=None):
        if context is None:
            context={}
        glinx = lambda conn, ps, jc: conn.server_id.wsfex_get_last_invoice_number(conn.id, ps, jc)[conn.server_id.id]
        glin = lambda conn, ps, jc: conn.server_id.wsfe_get_last_invoice_number(conn.id, ps, jc)[conn.server_id.id]
        r={}
        for journal in self.browse(cr, uid, ids):
            r[journal.id] = False
            conn = journal.afip_connection_id
            if conn and conn.server_id.code == 'wsfex':
                try:
                    r[journal.id] = glinx(conn, journal.point_of_sale, journal.journal_class_id.afip_code)
                except:
                    r[journal.id] = False
            if conn and conn.server_id.code == 'wsfe':
                try:
                    r[journal.id] = glin(conn, journal.point_of_sale, journal.journal_class_id.afip_code)
                except:
                    r[journal.id] = False
            _logger.debug("AFIP number of invoices in %s is %s" % (journal.name, r[journal.id]))
        return r
    
    _inherit = "account.journal"
    _columns = {
        'afip_state': fields.function(_get_fex_afip_state, type='selection', string='Connection state',
                                      method=True, readonly=True,
                                      selection=[
                                          ('connected','Connected'),
                                          ('connection_error','Connection Error'),
                                          ('connected_but_appserver_error','Application service has troubles'),
                                          ('connected_but_dbserver_error','Database service is down'),
                                          ('connected_but_authserver_error','Authentication service is down'),
                                          ('connected_but_servers_error','Services are down'),
                                          ('network_down','Network is down'),
                                          ('unknown_service','Unknown service'),
                                          ('connection_rejection','Connection reseted by host'),
                                          ('something_wrong','Not identified error'),
                                      ],
                            help="Connect to the AFIP and check service status."),
        'afip_items_generated': fields.function(_get_fex_afip_items_generated, type='integer', string='Number of Invoices Generated',method=True, 
                            help="Connect to the AFIP and check how many invoices was generated.", readonly=True),
    }

account_journal()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
