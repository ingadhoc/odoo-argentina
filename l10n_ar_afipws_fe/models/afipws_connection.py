# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
# from suds.client import Client
# from suds import WebFault
# from sslhttps import HttpsTransport
import logging

_logger = logging.getLogger(__name__)


class afipws_connection(models.Model):
    _inherit = "afipws.connection"

    afip_ws = fields.Selection(
        selection_add=[
            ('wsfe', 'Mercado interno -sin detalle- RG2485 (WSFEv1)'),
            ('wsfex', 'Exportación -con detalle- RG2758 (WSFEXv1)'),
            ('wsmtxca', 'Mercado interno -con detalle- RG2904 (WSMTXCA)'),
            ('wsbfe', 'Bono Fiscal -con detalle- RG2557 (WSMTXCA)'),
        ])

    @api.model
    def _connect(self, afip_ws):
        """
        Method to be inherited
        """
        ws = super(afipws_connection, self)._connect(afip_ws)
        if afip_ws == 'wsfe':
            from pyafipws.wsfev1 import WSFEv1
            ws = WSFEv1()
            ws.LanzarExcepciones = True
        elif afip_ws == "wsfex":
            from pyafipws.wsfexv1 import WSFEXv1
            ws = WSFEXv1()
        elif afip_ws == "wsmtxca":
            from pyafipws.wsmtx import WSMTXCA
            ws = WSMTXCA()
        return ws

    @api.model
    def get_afip_ws_url(self, afip_ws, environment_type):
        afip_ws_url = super(afipws_connection, self).get_afip_ws_url(
            afip_ws, environment_type)
        if afip_ws_url:
            return afip_ws_url
        elif afip_ws == 'wsfe':
            if environment_type == 'production':
                afip_ws_url = 'https://servicios1.afip.gov.ar/wsfev1/service.asmx'
            else:
                afip_ws_url = 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx'
        elif afip_ws == 'wsfex':
            if environment_type == 'production':
                afip_ws_url = 'https://servicios1.afip.gov.ar/wsfexv1/service.asmx'
            else:
                afip_ws_url = 'https://wswhomo.afip.gov.ar/wsfexv1/service.asmx'
        elif afip_ws in ('wsmtxca', 'wsbfe'):
            raise Warning('AFIP WS %s Not implemented yet' % afip_ws)
        return afip_ws_url

    # """
    # Ref: https://www.afip.gob.ar/fe/documentos/manual_desarrollador_COMPG_v2.pdf
    # TODO:
    #     AFIP Description: Método de obtención de CAEA (FECAEASolicitar)
    #     AFIP Description: Método de consulta de CAEA (FECAEAConsultar)
    #     AFIP Description: Método para informar CAEA sin movimiento (FECAEASinMovimientoInformar)
    #     AFIP Description: Método para informar comprobantes emitidos con CAEA (FECAEARegInformativo)
    #     AFIP Description: Método para consultar CAEA sin movimiento (FECAEASinMovimientoConsultar)
    #     AFIP Description: Recuperador de valores referenciales de códigos de Tipos de Alícuotas (FEParamGetTiposIva)
    #     AFIP Description: Recuperador de los puntos de venta asignados a Facturación Electrónica que soporten CAE y CAEA vía Web Services (FEParamGetPtosVenta)
    #     AFIP Description: Recuperador de cotización de moneda (FEParamGetCotizacion)
    #     AFIP Description: Recuperador de cantidad máxima de registros FECAESolicitar / FECAEARegInformativo (FECompTotXRequest)
    #     """

    # @api.multi
    # def get_ws_server(self, required_code):
    #     """
    #     Metodo para simplificar el codigo que chequa el tipo de ws, hace login
    #     y devuelve el servidor
    #     """
    #     self.ensure_one()
    #     srv = self.server_id

    #     # Ignore servers without code required_code.
    #     if self.server_id.code != required_code:
    #         _logger.warning(
    #             'Server id %i is code "%s" and this is a "%s" server' % (
    #                 srv.id, srv.code, required_code))

    #     # Login if nescesary.
    #     self.login()

    #     return srv

    # @api.multi
    # def wsfe_get_status(self):
    #     """
    #     AFIP Description: Método Dummy para verificación de funcionamiento de
    #     infraestructura (FEDummy)
    #     """
    #     self.check_afip_ws('wsfe')

    #     try:
    #         _logger.debug('Query AFIP Web service status')
    #         srvclient = Client(
    #             self.afip_ws_url+'?WSDL', transport=HttpsTransport())
    #         response = srvclient.service.FEDummy()
    #     except Exception as e:
    #         _logger.error('AFIP Web service error!: (%i) %s' % (
    #             e[0], e[1]))
    #         raise Warning(_(
    #             'AFIP Web service error. System return error %i: %s') % (
    #             e[0], e[1]))
    #     res = response
    #     _logger.info('Result %s' % res)
    #     return res

    # @api.multi
    # def wsfe_get_last_invoice_number(self, ptoVta, cbteTipo):
    #     """
    #     Get last ID number from AFIP

    #     AFIP Description: Recuperador de ultimo valor de comprobante registrado
    #     (FECompUltimoAutorizado)
    #     """
    #     self.check_afip_ws('wsfe')

    #     try:
    #         _logger.info('Take last invoice number from AFIP Web service\
    #             (pto vta: %s, cbte tipo: %s)' % (ptoVta, cbteTipo))
    #         srvclient = Client(
    #             self.afip_ws_url+'?WSDL', transport=HttpsTransport())
    #         response = srvclient.service.FECompUltimoAutorizado(
    #             Auth=self.get_auth(), PtoVta=ptoVta, CbteTipo=cbteTipo)

    #     except Exception as e:
    #         _logger.error(
    #             'AFIP Web service error!: (%i) %s' % (e[0], e[1]))
    #         raise Warning(_(
    #                 'AFIP Web service error.\n'
    #                 'Systemreturn error %i: %s\n'
    #                 'Pueda que esté intente realizar esta operación'
    #                 'desde el servidor de homologación.'
    #                 'Intente desde el servidor de producción.') %
    #             (e[0], e[1]))

    #     if hasattr(response, 'Errors'):
    #         for e in response.Errors.Err:
    #             _logger.error(
    #                 'AFIP Web service error!: (%i) %s' % (e.Code, e.Msg))
    #         res = False
    #     else:
    #         res = int(response.CbteNro)
    #     return res

    # @api.multi
    # def wsfe_get_cae(self, invoice_request):
    #     """
    #     Get CAE.

    #     AFIP Description: Método de autorización de comprobantes electrónicos
    #     por CAE (FECAESolicitar)
    #     """
    #     self.check_afip_ws('wsfe')
    #     res = False

    #     _logger.info('Get CAE from AFIP Web service')

    #     try:
    #         srvclient = Client(
    #             self.afip_ws_url+'?WSDL', transport=HttpsTransport())
    #         first = invoice_request.keys()[0]
    #         soapRequest = [{'FeCabReq': {
    #             'CantReg': len(invoice_request),
    #             'PtoVta': invoice_request[first]['PtoVta'],
    #             'CbteTipo': invoice_request[first]['CbteTipo']},
    #             'FeDetReq': [{'FECAEDetRequest': dict(
    #                 [(k, v) for k, v in req.iteritems()
    #                     if k not in [
    #                     'CantReg', 'PtoVta', 'CbteTipo']])}
    #                         for req in invoice_request.itervalues()]}]
    #         response = srvclient.service.FECAESolicitar(
    #             Auth=self.get_auth(),
    #             FeCAEReq=soapRequest,
    #         )
    #     except WebFault as e:
    #         _logger.error('AFIP Web service error!: %s' % (e[0]))
    #         raise Warning(_(
    #             'AFIP Web service error. System return error: %s') % e[0])
    #     except Exception as e:
    #         _logger.error('AFIP Web service error!: %s' % (str(e)))
    #         raise Warning(_(
    #             'AFIP Web service error, System return error "%s"' %
    #             (str(e))))

    #     common_error = [(e.Code, unicode(e.Msg)) for e in response.Errors[
    #         0]]if response.FeCabResp.Resultado in ["P", "R"] and hasattr(
    #             response, 'Errors') else []
    #     _logger.error('Request error: %s' % (common_error,))

    #     for resp in response.FeDetResp.FECAEDetResponse:
    #         if resp.Resultado == 'R':
    #             # Existe Error!
    #             _logger.error('Invoice error: %s' % (resp,))
    #             res = {
    #                 'CbteDesde': resp.CbteDesde,
    #                 'CbteHasta': resp.CbteHasta,
    #                 'Observaciones': [(o.Code, unicode(
    #                     o.Msg)) for o in resp.Observaciones.Obs] if hasattr(
    #                         resp, 'Observaciones') else [],
    #                 'Errores': common_error + [(e.Code, unicode(
    #                     e.Msg)) for e in response.Errors.Err] if hasattr(
    #                         response, 'Errors') else [],
    #             }
    #         else:
    #             # Todo bien!
    #             res = {
    #                 'CbteDesde': resp.CbteDesde,
    #                 'CbteHasta': resp.CbteHasta,
    #                 'CAE': resp.CAE,
    #                 'CAEFchVto': resp.CAEFchVto,
    #                 'Request': soapRequest,
    #                 'Response': response,
    #             }
    #     return res

    # @api.multi
    # def wsfe_query_invoice(self, cbteTipo, cbteNro, ptoVta):
    #     """
    #     Query for invoice stored by AFIP Web service.

    #     AFIP Description: Método para consultar Comprobantes Emitidos y su
    #     código (FECompConsultar)
    #     """
    #     self.check_afip_ws('wsfe')
    #     res = False
    #     try:
    #         _logger.info('Query for invoice stored by AFIP Web service')
    #         srvclient = Client(
    #             self.afip_ws_url+'?WSDL', transport=HttpsTransport())
    #         response = srvclient.service.FECompConsultar(
    #             Auth=self.get_auth(),
    #             FeCompConsReq={
    #                 'CbteTipo': cbteTipo,
    #                 'CbteNro': cbteNro,
    #                 'PtoVta': ptoVta,
    #                                                  })
    #     except Exception as e:
    #         _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
    #         raise Warning(_(
    #             'AFIP Web service error'
    #             'System return error %i: %s\n'
    #             'Pueda que esté intente realizar esta operación'
    #             'desde el servidor de homologación.'
    #             'Intente desde el servidor de producción.') % (e[0], e[1]))

    #     if hasattr(response, 'Errors'):
    #         for e in response.Errors.Err:
    #             _logger.error('AFIP Web service error!: (%i) %s' % (
    #                 e.Code, e.Msg))
    #     else:
    #         res = {
    #             'Concepto': response.ResultGet.Concepto,
    #             'DocTipo': response.ResultGet.DocTipo,
    #             'DocNro': response.ResultGet.DocNro,
    #             'CbteDesde': response.ResultGet.CbteDesde,
    #             'CbteHasta': response.ResultGet.CbteHasta,
    #             'CbteFch': response.ResultGet.CbteFch,
    #             'ImpTotal': response.ResultGet.ImpTotal,
    #             'ImpTotConc': response.ResultGet.ImpTotConc,
    #             'ImpNeto': response.ResultGet.ImpNeto,
    #             'ImpOpEx': response.ResultGet.ImpOpEx,
    #             'ImpTrib': response.ResultGet.ImpTrib,
    #             'ImpIVA': response.ResultGet.ImpIVA,
    #             'FchServDesde': response.ResultGet.FchServDesde,
    #             'FchServHasta': response.ResultGet.FchServHasta,
    #             'FchVtoPago': response.ResultGet.FchVtoPago,
    #             'MonId': response.ResultGet.MonId,
    #             'MonCotiz': response.ResultGet.MonCotiz,
    #             'Resultado': response.ResultGet.Resultado,
    #             'CodAutorizacion': response.ResultGet.CodAutorizacion,
    #             'EmisionTipo': response.ResultGet.EmisionTipo,
    #             'FchVto': response.ResultGet.FchVto,
    #             'FchProceso': response.ResultGet.FchProceso,
    #             'PtoVta': response.ResultGet.PtoVta,
    #             'CbteTipo': response.ResultGet.CbteTipo,
    #         }

    #     return res
