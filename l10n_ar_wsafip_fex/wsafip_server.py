# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Elepe Servicios (http://www.elepeservicios.com.ar)
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
from suds.client import Client
from suds import WebFault
import logging
import sys
from sslhttps import HttpsTransport

#~ logging.getLogger('suds.transport').setLevel(logging.DEBUG)
_logger = logging.getLogger(__name__)

def _update_incoterms(pool, cr, uid, model_name, remote_list, can_create=True, domain=[]):
    #~ import pdb; pdb.set_trace()
    model_obj = pool.get(model_name) 

    # Build set of AFIP codes
    rem_afip_code_set = set([ i['afip_export_incoterm_code'] for i in remote_list ])

    # Take exists instances 
    sto_ids = model_obj.search(cr, uid, domain)
    sto_list = model_obj.read(cr, uid, sto_ids, ['afip_export_incoterm_code'])
    sto_afip_code_set = set([ i['afip_export_incoterm_code'] for i in sto_list ])

    # Append new afip_code
    to_append = rem_afip_code_set - sto_afip_code_set
    if to_append and can_create:
        for item in [ i for i in remote_list if i['afip_export_incoterm_code'] in to_append ]:
            model_obj.create(cr, uid, item)
    elif to_append and not can_create:
        _logger.warning('New items of type %s in WS. Wont be created.' % model_name)

    # Update active document types
    to_update = rem_afip_code_set & sto_afip_code_set
    update_dict = dict( [ (i['afip_export_incoterm_code'], i['active']) for i in remote_list
                         if i['afip_export_incoterm_code'] in to_update ])
    to_active = [ k for k,v in update_dict.items() if v ]
    if to_active:
        model_ids = model_obj.search(cr, uid, [('afip_export_incoterm_code','in',to_active),('active','in',['f',False])])
        model_obj.write(cr, uid, model_ids, {'active':True})

    to_deactive = [ k for k,v in update_dict.items() if not v ]
    if to_deactive:
        model_ids = model_obj.search(cr, uid, [('afip_export_incoterm_code','in',to_deactive),('active','in',['t',True])])
        model_obj.write(cr, uid, model_ids, {'active':False})

    # To disable exists local afip_code but not in remote
    #~ to_inactive = sto_afip_code_set - rem_afip_code_set 
    #~ if to_inactive:
        #~ model_ids = model_obj.search(cr, uid, [('afip_export_incoterm_code','in',list(to_inactive))])
        #~ model_obj.write(cr, uid, model_ids, {'active':False})

    _logger.info('Updated %s items' % model_name)

    return True
    
def _update_currency_rates(pool, cr, uid, model_name, remote_list, can_create=False, domain=[]):
    model_obj = pool.get(model_name)

    # Set ID and RATE for each currency
    remote_id_rate = []
    for id, rate in remote_list.iteritems(): remote_id_rate.append([id, rate])
    
    for currency in remote_id_rate:
        curr_id = model_obj.search(cr,uid,[('currency_id','=',currency[0])])
        adapted_rate = 1/currency[1]
        model_obj.write(cr, uid, curr_id, {'rate': adapted_rate})
    
    string_busqueda = ["ARS"]
    cr.execute("SELECT id FROM res_currency WHERE name=%s", string_busqueda)
    afip_pesos_arg_code = [cr.fetchall()[0][0]]
    cr.execute("UPDATE res_currency_rate SET rate=1.000000 WHERE currency_id=%s",afip_pesos_arg_code)

    _logger.info('Updated currency rates!')

    return True

class wsafip_server(osv.osv):
    _name = "wsafip.server"
    _inherit = "wsafip.server"

    """
    Ref: http://www.afip.gob.ar/fe/documentos/WSFEX-Manualparaeldesarrollador_V1.pdf
    TODO:
        AFIP Description: Recupera los datos completos de un comprobante ya autorizado (FEXGetCMP)
        AFIP Description: Recupera la cotizacion de la moneda consultada y su fecha (FEXGetPARAM_Ctz)
        AFIP Description: Recupera el listado de paises (FEXGetPARAM_DST_pais)
    """

    def wsfex_get_status(self, cr, uid, ids, conn_id, context=None):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento de infraestructura (FEXDummy)
        """
        conn_obj = self.pool.get('wsafip.connection')

        r = {}
        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex': continue

            conn = conn_obj.browse(cr, uid, conn_id, context=context) 
            conn.login() # Login if nescesary.

            try:
                _logger.debug('Query AFIP Web service status')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FEXDummy()
                
            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') % (e[0], e[1]))
            r[srv.id] = (response.AuthServer,
                         response.AppServer,
                         response.DbServer)
        return r

    def wsfex_update_incoterms(self, cr, uid, ids, conn_id, context=None):
        """
        Updates the list of available Incoterms.

        AFIP Description: Recupera el listado Incoterms utilizables en servicio de autorizacion (FEXGetPARAM_Incoterms)
        """
        conn_obj = self.pool.get('wsafip.connection')

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex': continue

            # Take the connection, continue if connected or clockshifted
            conn = conn_obj.browse(cr, uid, conn_id, context=context) 
            conn.login() # Login if necessary.
            if conn.state not in  [ 'connected', 'clockshifted' ]: continue

            # Build request
            try:
                _logger.debug('Updating list of Incoterms from AFIP Web service')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FEXGetPARAM_Incoterms(Auth=conn.get_auth())

                # Take list of available Incoterms
                incoterms_list = [
                    {'afip_export_incoterm_code': res.Inc_Id,
                     'afip_export_incoterm_desc': res.Inc_Ds }
                    for res in response.FEXResultGet.ClsFEXResponse_Inc ]
                    
            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') % (e[0], e[1]))

            _update_incoterms(self.pool, cr, uid,
                    'afip.incoterms',
                    incoterms_list,
                    can_create=True
                   )

        return
        
    def wsfex_update_currency_rates(self, cr, uid, ids, conn_id, context=None):
        """
        Updates the rates of available Currencies.

        AFIP Description: Recupera la cotizacion de la moneda consultada y su fecha (FEXGetPARAM_Ctz)
        """
        conn_obj = self.pool.get('wsafip.connection')
        currency_rates = {}
        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex': continue

            # Take the connection, continue if connected or clockshifted
            conn = conn_obj.browse(cr, uid, conn_id, context=context) 
            conn.login() # Login if necessary.
            if conn.state not in  [ 'connected', 'clockshifted' ]: continue

            # Build request
            try:
                _logger.debug('Updating rates of Currencies from AFIP Web service')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                cr.execute("SELECT id, afip_code FROM res_currency WHERE afip_code is not NULL ORDER BY id")
                list_of_currencies = cr.fetchall()
                
                for currency_id, afip_code in list_of_currencies:
                    response = srvclient.service.FEXGetPARAM_Ctz(Auth=conn.get_auth(), Mon_id=afip_code)
                    if (response.FEXErr.ErrCode != 0):
                        # Existe Error!
                        _logger.error('Invalid currency code/No currency rate available for id: %s, code: %s!', currency_id, afip_code)
                        continue

                    currency_rates[currency_id] = response.FEXResultGet.Mon_ctz
                    
            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') % (e[0], e[1]))

            _update_currency_rates(self.pool, cr, uid,
                    'res.currency.rate',
                    currency_rates,
                    can_create=False
                   )

        return

    def wsfex_get_last_invoice_number(self, cr, uid, ids, conn_id, ptoVta, cbteTipo, context=None):
        """
        Get last invoice number from AFIP

        AFIP Description: Recupera el ultimo comprobante autorizado (FEXGetLast_CMP)
        """
        conn_obj = self.pool.get('wsafip.connection')
        #~ import pdb; pdb.set_trace()
        r={}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex': continue

            # Take the connection
            conn = conn_obj.browse(cr, uid, conn_id, context=context) 
            conn.login() # Login if necessary.
            if conn.state not in  [ 'connected', 'clockshifted' ]:
                r[srv.id] = False
                continue

            try:
                #~ import pdb; pdb.set_trace()
                _logger.info('Take last invoice number from AFIP Web service')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                auth = conn.get_auth()
                auth['Cbte_Tipo'] = cbteTipo
                auth['Pto_venta'] = ptoVta
                response = srvclient.service.FEXGetLast_CMP(auth)

            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s\n'
                                       u'Pueda que esté intente realizar esta operación'
                                       u'desde el servidor de homologación.'
                                       u'Intente desde el servidor de producción.') % (e[0], e[1]))
            if (response.FEXErr.ErrCode != 0):
                # Existe Error!
                _logger.error('AFIP Web service error!: (%i) %s' % (response.FEXErr.ErrCode, response.FEXErr.ErrMsg))
                r[srv.id] = False
            else:
                r[srv.id] = int(response.FEXResult_LastCMP.Cbte_nro)
        return r
        
    def wsfex_get_last_id(self, cr, uid, ids, conn_id, context=None):
        """
        Get Last ID number from AFIP.

        AFIP Description: Recupera el ultimo ID (FEXGetLast_ID) 
        """
        conn_obj = self.pool.get('wsafip.connection')
        #~ import pdb; pdb.set_trace()
        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex': continue

            # Take the connection
            conn = conn_obj.browse(cr, uid, conn_id, context=context) 
            conn.login() # Login if necessary.
            if conn.state not in  [ 'connected', 'clockshifted' ]:
                r[srv.id] = False
                continue

            try:
                _logger.info('Take last ID number from AFIP Web service')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FEXGetLast_ID(Auth=conn.get_auth())

            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s\n'
                                       u'Pueda que esté intente realizar esta operación'
                                       u'desde el servidor de homologación.'
                                       u'Intente desde el servidor de producción.') % (e[0], e[1]))
            
            if (response.FEXErr.ErrCode != 0):
                # Existe Error!
                _logger.error('AFIP Web service error!: (%i) %s' % (response.FEXErr.ErrCode, response.FEXErr.ErrMsg))
                r = False
            else:
                r = int(response.FEXResultGet.Id)
        return r
    
    def wsfex_check_permissions(self, cr, uid, ids, conn_id, id_permiso, dst_merc, context=None):
        """
        Check shipment/destination country permissions from AFIP

        AFIP Description: Verifica la existencia de la permiso/pais de destinación de embarque ingresado (FEXCheck_Permiso)
        """
        conn_obj = self.pool.get('wsafip.connection')

        r={}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex': continue

            # Take the connection
            conn = conn_obj.browse(cr, uid, conn_id, context=context) 
            conn.login() # Login if necessary.
            if conn.state not in  [ 'connected', 'clockshifted' ]:
                r[srv.id] = False
                continue

            try:
                _logger.info('Check shipment/destination country permissions from AFIP Web service')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FEXCheck_Permiso(Auth=conn.get_auth(), ID_Permiso=id_permiso, Dst_merc=dst_merc)

            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s\n'
                                       u'Pueda que esté intente realizar esta operación'
                                       u'desde el servidor de homologación.'
                                       u'Intente desde el servidor de producción.') % (e[0], e[1]))

            if hasattr(response, 'Errors'):
                for e in response.Errors.Err:
                    code = e.Code
                    _logger.error('AFIP Web service error!: (%i) %s' % (e.Code, e.Msg))
                r[srv.id] = False
            else:
                r[srv.id] = str(response.FEXResultGet.Status)
        return r
        
    def wsfex_get_cae(self, cr, uid, ids, conn_id, invoice_request, context=None):
        """
        Get CAE.

        AFIP Description: Autoriza un comprobante, devolviendo su CAE correspondiente (FEXAuthorize)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex': continue

            # Take the connection
            conn = conn_obj.browse(cr, uid, conn_id, context=context) 
            conn.login() # Login if necessary.
            if conn.state not in  [ 'connected', 'clockshifted' ]: continue

            _logger.info('Get CAE from AFIP Web service')

            try:
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                first = invoice_request.keys()[0]
                #~ import pdb; pdb.set_trace()
                response = srvclient.service.FEXAuthorize(Auth=conn.get_auth(),
                    Cmp = [dict([(k,v) for k,v in req.iteritems()]) for req in invoice_request.itervalues()]
                )
                
            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') % (e[0], e[1]))


            soapmessage = [dict([(k,v) for k,v in req.iteritems()]) for req in invoice_request.itervalues()]
            cbte_nro = soapmessage[0].get('Cbte_nro')
            
            #~ import pdb; pdb.set_trace()
            
            if (response.FEXErr.ErrCode != 0):
                # Existe Error!
                _logger.error('Rejected invoice!')

                r[cbte_nro]={
                    'Eventos': [ (o[0], unicode(o[1])) for o in response.FEXEvents ] if (hasattr(response, 'FEXEvents') and response.FEXEvents.EventCode != 0) else [],
                    'Errores': [ (e[0], unicode(e[1])) for e in response.FEXErr ]    if (hasattr(response, 'FEXErr')    and response.FEXErr.ErrCode != 0)      else [],
                }
            else:
                # Todo bien!
                r[cbte_nro]={
                    'CAE': response.FEXResultAuth.Cae,
                    'CAEFchVto': response.FEXResultAuth.Fch_venc_Cae,
                    'Request': soapmessage,
                    'Response': response,
                }
        return r


wsafip_server()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
