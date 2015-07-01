# -*- coding: utf-8 -*-
from openerp import models, api, _
from suds.client import Client
from suds import WebFault
from sslhttps import HttpsTransport
import logging

_logger = logging.getLogger(__name__)


class wsafip_connection(models.Model):
    _inherit = "wsafip.connection"

    """
    Ref: https://www.afip.gob.ar/fe/documentos/manual_desarrollador_COMPG_v2.pdf
    TODO:
        AFIP Description: Método de obtención de CAEA (FECAEASolicitar)
        AFIP Description: Método de consulta de CAEA (FECAEAConsultar)
        AFIP Description: Método para informar CAEA sin movimiento (FECAEASinMovimientoInformar)
        AFIP Description: Método para informar comprobantes emitidos con CAEA (FECAEARegInformativo)
        AFIP Description: Método para consultar CAEA sin movimiento (FECAEASinMovimientoConsultar)
        AFIP Description: Recuperador de valores referenciales de códigos de Tipos de Alícuotas (FEParamGetTiposIva)
        AFIP Description: Recuperador de los puntos de venta asignados a Facturación Electrónica que soporten CAE y CAEA vía Web Services (FEParamGetPtosVenta)
        AFIP Description: Recuperador de cotización de moneda (FEParamGetCotizacion)
        AFIP Description: Recuperador de cantidad máxima de registros FECAESolicitar / FECAEARegInformativo (FECompTotXRequest)
        """

    @api.model
    def update_model_data(
            self, model_name, remote_list, can_create=True, domain=[]):
        """
        Generic method used to update records on a model when getting new
        information throw afip webservices
        """
        model = self.env[model_name]

        # Build set of AFIP codes
        remote_afip_codes = set([x['afip_code'] for x in remote_list])

        # Take exists instances
        actual_records = model.search(
            [('active', 'in', [False, True])] + domain)

        # sto_list = model.read(cr, uid, sto_ids, ['afip_code'])
        actual_afip_codes = set(actual_records.mapped('afip_code'))

        # Append new afip_code
        new_afip_codes = remote_afip_codes - actual_afip_codes

        if new_afip_codes and can_create:
            for item in [x for x in remote_list if x[
                    'afip_code'] in new_afip_codes]:
                model.create(item)
        elif new_afip_codes and not can_create:
            _logger.warning(
                'New items of type %s in WS. I will not create them.' % (
                    model_name))

        # Update active document types
        to_update = remote_afip_codes & actual_afip_codes
        update_dict = dict([(x['afip_code'], x['active']) for i in remote_list if x['afip_code'] in to_update])

        to_active = [k for k, v in update_dict.items() if v]

        if to_active:
            records_to_active = model.search([
                ('afip_code', 'in', to_active),
                ('active', '=', False)])
            records_to_active.write({'active': True})

        to_deactive = [k for k, v in update_dict.items() if not v]
        if to_deactive:
            records_to_deactive = model.search([
                ('afip_code', 'in', to_deactive),
                ('active', '=', True)])
            records_to_deactive.write({'active': False})

        # TODO que es este y que el anterior?
        # To disable exists local afip_code but not in remote
        to_inactive = actual_afip_codes - remote_afip_codes
        if to_inactive:
            records_to_inactive = model.search([
                ('afip_code', 'in', list(to_inactive))])
            records_to_inactive.write({'active': False})

        _logger.info('Updated %s items' % model_name)
        return True

    @api.multi
    def get_ws_server(self, required_code):
        """
        Metodo para simplificar el codigo que chequa el tipo de ws, hace login
        y devuelve el servidor
        """
        self.ensure_one()
        srv = self.server_id

        # Ignore servers without code required_code.
        if self.server_id.code != required_code:
            _logger.warning(
                'Server id %i is code "%s" and this is a "%s" server' % (
                    srv.id, srv.code, required_code))

        # Login if nescesary.
        self.login()

        return srv

    @api.multi
    def wsfe_get_status(self):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento de
        infraestructura (FEDummy)
        """
        srv = self.get_ws_server('wsfe')

        try:
            _logger.debug('Query AFIP Web service status')
            srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
            response = srvclient.service.FEDummy()
        except Exception as e:
            _logger.error('AFIP Web service error!: (%i) %s' % (
                e[0], e[1]))
            raise Warning(_(
                'AFIP Web service error. System return error %i: %s') % (
                e[0], e[1]))
        return (response.AuthServer, response.AppServer, response.DbServer)

    @api.multi
    def wsfe_update_afip_concept_type(self):
        """
        Update concepts class.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de Conceptos (FEParamGetTiposConcepto)
        """
        srv = self.get_ws_server('wsfe')

        try:
            _logger.debug('Updating concept class from AFIP Web service')
            srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
            response = srvclient.service.FEParamGetTiposConcepto(
                Auth=self.get_auth())

            # Take list of concept type
            concepttype_list = [
                {'afip_code': ct.Id,
                 'name': ct.Desc,
                 'active': ct.FchHasta in [None, 'NULL']}
                for ct in response.ResultGet.ConceptoTipo]
        except Exception as e:
            _logger.error(
                'AFIP Web service error!: (%i) %s' % (e[0], e[1]))
            raise Warning(_(
                'AFIP Web service error. System return error %i: %s') % (
                    e[0], e[1]))

        self.update_model_data(
            'afip.concept_type',
            concepttype_list,
            can_create=True,
            domain=[('afip_code', '!=', 0)])

    @api.multi
    def wsfe_update_journal_class(self):
        """
        Update journal class.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de comprobante (FEParamGetTiposCbte)
        """
        srv = self.get_ws_server('wsfe')
        try:
            _logger.info('Updating journal class from AFIP Web service')
            srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
            response = srvclient.service.FEParamGetTiposCbte(
                Auth=self.get_auth())

            # Take list of journal class
            journalclass_list = [
                {'afip_code': c.Id,
                    'name': c.Desc,
                    'active': c.FchHasta in [None, 'NULL']}
                for c in response.ResultGet.CbteTipo
            ]
        except Exception as e:
            _logger.error(
                'AFIP Web service error!: (%i) %s' % (e[0], e[1]))
            raise Warning(_(
                'AFIP Web service error. System return error %i: %s') % (
                e[0], e[1]))

        self.update_model_data(
            'afip.journal_class',
            journalclass_list,
            can_create=False,
            domain=[('afip_code', '!=', 0)])

    @api.multi
    def wsfe_update_document_type(self):
        """
        Update document type.
        This function must be called from connection model.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de Documentos (FEParamGetTiposDoc)
        """
        srv = self.get_ws_server('wsfe')

        try:
            _logger.info('Updating document types from AFIP Web service')
            srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
            response = srvclient.service.FEParamGetTiposDoc(
                Auth=self.get_auth())

            # Take list of document types
            doctype_list = [
                {'afip_code': c.Id,
                    'name': c.Desc,
                    'code': c.Desc,
                    'active': c.FchHasta in [None, 'NULL']}
                for c in response.ResultGet.DocTipo
            ]
        except Exception as e:
            _logger.error(
                'AFIP Web service error!: (%i) %s' % (e[0], e[1]))
            raise Warning(_(
                'AFIP Web service error System return error %i: %s') % (
                    e[0], e[1]))

        self.update_model_data(
            'afip.document_type',
            doctype_list,
            can_create=True,
            domain=[])

    @api.multi
    def wsfe_update_optional_types(self):
        """
        Update optional types.
        This function must be called from connection model.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de datos Opcionales (FEParamGetTiposOpcional)
        """
        srv = self.get_ws_server('wsfe')

        try:
            _logger.info('Updating currency from AFIP Web service')
            srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
            response = srvclient.service.FEParamGetTiposOpcional(
                Auth=self.get_auth())

            # Take list of currency
            currency_list = [
                {'afip_code': c.Id,
                    'name': c.Desc,
                    'active': c.FchHasta in [None, 'NULL']}
                for c in response.ResultGet.OpcionalTipo
            ]
        except Exception as e:
            _logger.error(
                'AFIP Web service error!: (%i) %s' % (e[0], e[1]))
            raise Warning(_(
                'AFIP Web service error. System return error %i: %s') % (
                    e[0], e[1]))

        self.update_model_data(
            'afip.optional_type',
            currency_list,
            can_create=True,
            domain=[])

    @api.multi
    def wsfe_update_currency(self):
        """
        Update currency. This function must be called from connection model.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de Monedas (FEParamGetTiposMonedas)
        """

        srv = self.get_ws_server('wsfe')

        try:
            _logger.info('Updating currency from AFIP Web service')
            srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
            response = srvclient.service.FEParamGetTiposMonedas(
                Auth=self.get_auth())

            # Take list of currency
            currency_list = [
                {'afip_code': c.Id,
                    'name': c.Desc,
                    'active': c.FchHasta in [None, 'NULL']}
                for c in response.ResultGet.Moneda
            ]
        except Exception as e:
            _logger.error(
                'AFIP Web service error!: (%i) %s' % (e[0], e[1]))
            raise Warning(_(
                'AFIP Web service error. System return error %i: %s') % (
                e[0], e[1]))

        self.update_model_data(
            'res.currency',
            currency_list,
            can_create=False,
            domain=[])

    # def wsfe_update_tax(self, cr, uid, ids, conn_id, context=None):
    #     """
    #     Update taxes. This function must be called from connection model.

    #     AFIP Description: Recuperador de valores referenciales de códigos de
    #     Tipos de Tributos (FEParamGetTiposTributos)
    #     """
    #     conn_obj = self.pool.get('wsafip.connection')

    #     for srv in self.browse(cr, uid, ids, context=context):
    #         # Ignore servers without code WSFE.
    #         if srv.code != 'wsfe':
    #             continue

    #         # Take the connection, continue if connected or clockshifted
    #         conn = conn_obj.browse(cr, uid, conn_id, context=context)
    #         conn.login()  # Login if nescesary.
    #         if conn.state not in ['connected', 'clockshifted']:
    #             continue

    #         _escape_ = lambda s: s.replace('%', '%%')

    #         try:
    #             _logger.info('Updating currency from AFIP Web service')
    #             srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
    #             response = srvclient.service.FEParamGetTiposTributos(
    #                 Auth=conn.get_auth())

    #             # Take list of taxes
    #             tax_list = [
    #                 {'afip_code': c.Id,
    #                     'name': c.Desc}
    #                 for c in response.ResultGet.TributoTipo
    #             ]

    #             # Take IVA codes
    #             response = srvclient.service.FEParamGetTiposIva(
    #                 Auth=conn.get_auth())
    #             tax_list.extend([
    #                 {'afip_code': c.Id,
    #                     'name': "%s" % _escape_(c.Desc)}
    #                 for c in response.ResultGet.IvaTipo
    #             ])

    #         except Exception as e:
    #             _logger.error(
    #                 'AFIP Web service error!: %s' % (e))
    #             raise osv.except_osv(
    #                 _(u'AFIP Web service error'),
    #                 _(u'System return error: %s') % (e))

    #         tax_code_obj = self.pool.get('account.tax.code')

    #         for tc in tax_list:
    #             tax_code_ids = tax_code_obj.search(
    #                 cr, uid, [('name', '=like', '% ' + tc['name'])])
    #             _logger.debug(
    #                 "Tax '%s' match with %s" % (tc['name'], tax_code_ids))
    #             if tax_code_ids:
    #                 w = dict(tc)
    #                 del w['name']
    #                 tax_code_obj.write(cr, uid, tax_code_ids, w)

    #     return True

    # def wsfe_get_last_invoice_number(
    #         self, cr, uid, ids, conn_id, ptoVta, cbteTipo, context=None):
    #     """
    #     Get last ID number from AFIP

    #     AFIP Description: Recuperador de ultimo valor de comprobante registrado
    #     (FECompUltimoAutorizado)
    #     """
    #     conn_obj = self.pool.get('wsafip.connection')

    #     r = {}

    #     for srv in self.browse(cr, uid, ids, context=context):
    #         # Ignore servers without code WSFE.
    #         if srv.code != 'wsfe':
    #             continue

    #         # Take the connection
    #         conn = conn_obj.browse(cr, uid, conn_id, context=context)
    #         conn.login()  # Login if nescesary.
    #         if conn.state not in ['connected', 'clockshifted']:
    #             r[srv.id] = False
    #             continue

    #         try:
    #             _logger.info('Take last invoice number from AFIP Web service\
    #                 (pto vta: %s, cbte tipo: %s)' % (ptoVta, cbteTipo))
    #             srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
    #             response = srvclient.service.FECompUltimoAutorizado(
    #                 Auth=conn.get_auth(), PtoVta=ptoVta, CbteTipo=cbteTipo)

    #         except Exception as e:
    #             _logger.error(
    #                 'AFIP Web service error!: (%i) %s' % (e[0], e[1]))
    #             raise osv.except_osv(
    #                 _(u'AFIP Web service error'),
    #                 _(u'System return error %i: %s\n'
    #                     u'Pueda que esté intente realizar esta operación'
    #                     u'desde el servidor de homologación.'
    #                     u'Intente desde el servidor de producción.') %
    #                 (e[0], e[1]))

    #         if hasattr(response, 'Errors'):
    #             for e in response.Errors.Err:
    #                 _logger.error(
    #                     'AFIP Web service error!: (%i) %s' % (e.Code, e.Msg))
    #             r[srv.id] = False
    #         else:
    #             r[srv.id] = int(response.CbteNro)
    #     return r

    # def wsfe_get_cae(
    #         self, cr, uid, ids, conn_id, invoice_request, context=None):
    #     """
    #     Get CAE.

    #     AFIP Description: Método de autorización de comprobantes electrónicos
    #     por CAE (FECAESolicitar)
    #     """
    #     conn_obj = self.pool.get('wsafip.connection')
    #     r = {}

    #     for srv in self.browse(cr, uid, ids, context=context):
    #         # Ignore servers without code WSFE.
    #         if srv.code != 'wsfe':
    #             raise Warning(_('Service code is "%s" and should be "wsfe" for electronic invoice"' % (
    #                 srv.code)))
    #             # continue

    #         # Take the connection
    #         conn = conn_obj.browse(cr, uid, conn_id, context=context)
    #         conn.login()  # Login if nescesary.
    #         if conn.state not in ['connected', 'clockshifted']:
    #             raise Warning(_('Could not connect on connection %s' % (
    #                 conn.name)))
    #             # continue

    #         _logger.info('Get CAE from AFIP Web service')

    #         try:
    #             srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
    #             first = invoice_request.keys()[0]
    #             response = srvclient.service.FECAESolicitar(
    #                 Auth=conn.get_auth(),
    #                 FeCAEReq=[{
    #                     'FeCabReq': {
    #                         'CantReg': len(invoice_request),
    #                         'PtoVta': invoice_request[first]['PtoVta'],
    #                         'CbteTipo': invoice_request[first]['CbteTipo'],
    #                     },
    #                     'FeDetReq': [
    #                         {'FECAEDetRequest': dict(
    #                         [(k, v) for k,v in req.iteritems()
    #                         if k not in ['CantReg', 'PtoVta', 'CbteTipo']])}
    #                         for req in invoice_request.itervalues()
    #                     ],
    #                 }]
    #             )
    #         except WebFault as e:
    #             _logger.error('AFIP Web service error!: %s' % (e[0]))
    #             raise osv.except_osv(_(u'AFIP Web service error'),
    #                                  _(u'System return error: %s') % e[0])
    #         except Exception as e:
    #             _logger.error('AFIP Web service error!: %s' % (str(e)))
    #             raise Warning(_(
    #                 'AFIP Web service error, System return error "%s"' %
    #                 (str(e))))

    #         soapRequest = [{'FeCabReq': {
    #             'CantReg': len(invoice_request),
    #             'PtoVta': invoice_request[first]['PtoVta'],
    #             'CbteTipo': invoice_request[first]['CbteTipo']},
    #             'FeDetReq': [{'FECAEDetRequest': dict(
    #                 [(k, v) for k,v in req.iteritems() if k not in ['CantReg', 'PtoVta', 'CbteTipo']])} for req in invoice_request.itervalues()],}]

    #         common_error = [(e.Code, unicode(e.Msg)) for e in response.Errors[0]] if response.FeCabResp.Resultado in ["P", "R"] and hasattr(response, 'Errors') else []
    #         _logger.error('Request error: %s' % (common_error,))

    #         for resp in response.FeDetResp.FECAEDetResponse:
    #             if resp.Resultado == 'R':
    #                 # Existe Error!
    #                 _logger.error('Invoice error: %s' % (resp,))
    #                 r[int(resp.CbteDesde)]={
    #                     'CbteDesde': resp.CbteDesde,
    #                     'CbteHasta': resp.CbteHasta,
    #                     'Observaciones': [ (o.Code, unicode(o.Msg)) for o in resp.Observaciones.Obs ]
    #                             if hasattr(resp,'Observaciones') else [],
    #                     'Errores': common_error + [ (e.Code, unicode(e.Msg)) for e in response.Errors.Err ]
    #                             if hasattr(response, 'Errors') else [],
    #                 }
    #             else:
    #                 # Todo bien!
    #                 r[int(resp.CbteDesde)]={
    #                     'CbteDesde': resp.CbteDesde,
    #                     'CbteHasta': resp.CbteHasta,
    #                     'CAE': resp.CAE,
    #                     'CAEFchVto': resp.CAEFchVto,
    #                     'Request': soapRequest,
    #                     'Response': response,
    #                 }
    #     return r

    # def wsfe_query_invoice(self, cr, uid, ids, conn_id, cbteTipo, cbteNro, ptoVta, context=None):
    #     """
    #     Query for invoice stored by AFIP Web service.

    #     AFIP Description: Método para consultar Comprobantes Emitidos y su código (FECompConsultar)
    #     """
    #     conn_obj = self.pool.get('wsafip.connection')
    #     r = {}

    #     for srv in self.browse(cr, uid, ids, context=context):
    #         # Ignore servers without code WSFE.
    #         if srv.code != 'wsfe': continue

    #         # Take the connection
    #         conn = conn_obj.browse(cr, uid, conn_id, context=context) 
    #         conn.login() # Login if nescesary.

    #         try:
    #             _logger.info('Query for invoice stored by AFIP Web service')
    #             srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
    #             response = srvclient.service.FECompConsultar(Auth=conn.get_auth(),
    #                                                              FeCompConsReq={
    #                                                                  'CbteTipo': cbteTipo,
    #                                                                  'CbteNro': cbteNro,
    #                                                                  'PtoVta': ptoVta,
    #                                                              })
    #         except Exception as e:
    #             _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
    #             raise osv.except_osv(_(u'AFIP Web service error'),
    #                                  _(u'System return error %i: %s\n'
    #                                    u'Pueda que esté intente realizar esta operación'
    #                                    u'desde el servidor de homologación.'
    #                                    u'Intente desde el servidor de producción.') % (e[0], e[1]))

    #         if hasattr(response, 'Errors'):
    #             for e in response.Errors.Err:
    #                 code = e.Code
    #                 _logger.error('AFIP Web service error!: (%i) %s' % (e.Code, e.Msg))
    #             r[srv.id] = False
    #         else:
    #             r[srv.id] = { 
    #                 'Concepto': response.ResultGet.Concepto,
    #                 'DocTipo': response.ResultGet.DocTipo,
    #                 'DocNro': response.ResultGet.DocNro,
    #                 'CbteDesde': response.ResultGet.CbteDesde,
    #                 'CbteHasta': response.ResultGet.CbteHasta,
    #                 'CbteFch': response.ResultGet.CbteFch,
    #                 'ImpTotal': response.ResultGet.ImpTotal,
    #                 'ImpTotConc': response.ResultGet.ImpTotConc,
    #                 'ImpNeto': response.ResultGet.ImpNeto,
    #                 'ImpOpEx': response.ResultGet.ImpOpEx,
    #                 'ImpTrib': response.ResultGet.ImpTrib,
    #                 'ImpIVA': response.ResultGet.ImpIVA,
    #                 'FchServDesde': response.ResultGet.FchServDesde,
    #                 'FchServHasta': response.ResultGet.FchServHasta,
    #                 'FchVtoPago': response.ResultGet.FchVtoPago,
    #                 'MonId': response.ResultGet.MonId,
    #                 'MonCotiz': response.ResultGet.MonCotiz,
    #                 'Resultado': response.ResultGet.Resultado,
    #                 'CodAutorizacion': response.ResultGet.CodAutorizacion,
    #                 'EmisionTipo': response.ResultGet.EmisionTipo,
    #                 'FchVto': response.ResultGet.FchVto,
    #                 'FchProceso': response.ResultGet.FchProceso,
    #                 'PtoVta': response.ResultGet.PtoVta,
    #                 'CbteTipo': response.ResultGet.CbteTipo,
    #             }

    #     return r