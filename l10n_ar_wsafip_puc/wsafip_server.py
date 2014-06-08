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
from suds.client import Client
from suds import WebFault
import logging
import sys
from sslhttps import HttpsTransport

# logging.getLogger('suds.transport').setLevel(logging.DEBUG)

_logger = logging.getLogger(__name__)

class wsafip_server(osv.osv):
    _name = "wsafip.server"
    _inherit = "wsafip.server"

    """
    El servicio de Consulta de Padrón Nivel 3 y 10 permite que un organismo externo acceda a los datos de
    un contribuyente registrado en el Padrón de AFIP.
    """

    def wspuc_get_contribuyente(self, cr, uid, ids, conn_id, cuit, context=None):
        """
        Read contribuyente.

        getRequest
        """
        conn_obj = self.pool.get('wsafip.connection')

        import pdb; pdb.set_trace()

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFE.
            if srv.code.lower() not in ['wspn3', 'wspn10']: continue

            # Take the connection, continue if connected or clockshifted
            conn = conn_obj.browse(cr, uid, conn_id, context=context) 
            conn.login() # Login if nescesary.
            if conn.state not in  [ 'connected', 'clockshifted' ]: continue

            # Build request
            try:
                _logger.debug('Lectura del padrón de contribuyentes del AFIP')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FEParamGetTiposConcepto(Auth=conn.get_auth())

                # Take list of concept type
                concepttype_list = [
                    {'afip_code': ct.Id,
                     'name': ct.Desc,
                     'active': ct.FchHasta in [None, 'NULL'] }
                    for ct in response.ResultGet.ConceptoTipo ]
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') % (e[0], e[1]))

        return

wsafip_server()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
