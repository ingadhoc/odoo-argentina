##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AfipwsConnection(models.Model):
    _inherit = "afipws.connection"

    # TODO use _get_afip_ws_selection to add values to this selection
    afip_ws = fields.Selection(
        selection_add=[
            ('wsfe', 'Mercado interno -sin detalle- RG2485 (WSFEv1)'),
            ('wsmtxca', 'Mercado interno -con detalle- RG2904 (WSMTXCA)'),
            ('wsfex', 'Exportación -con detalle- RG2758 (WSFEXv1)'),
            ('wsbfe', 'Bono Fiscal -con detalle- RG2557 (WSBFE)'),
            ('wscdc', 'Constatación de Comprobantes (WSCDC)'),
        ])

    @api.model
    def _get_ws(self, afip_ws):
        """
        Method to be inherited
        """
        ws = super(AfipwsConnection, self)._get_ws(afip_ws)
        if afip_ws == 'wsfe':
            from pyafipws.wsfev1 import WSFEv1
            ws = WSFEv1()
        elif afip_ws == "wsfex":
            from pyafipws.wsfexv1 import WSFEXv1
            ws = WSFEXv1()
        elif afip_ws == "wsmtxca":
            from pyafipws.wsmtx import WSMTXCA
            ws = WSMTXCA()
        elif afip_ws == "wscdc":
            from pyafipws.wscdc import WSCDC
            ws = WSCDC()
        elif afip_ws == "wsbfe":
            from pyafipws.wsbfev1 import WSBFEv1
            ws = WSBFEv1()
        return ws

    @api.model
    def get_afip_ws_url(self, afip_ws, environment_type):
        afip_ws_url = super(AfipwsConnection, self).get_afip_ws_url(
            afip_ws, environment_type)
        if afip_ws_url:
            return afip_ws_url
        elif afip_ws == 'wsfe':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL')
            else:
                afip_ws_url = (
                    'https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL')
        elif afip_ws == 'wsfex':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://servicios1.afip.gov.ar/wsfexv1/service.asmx?WSDL')
            else:
                afip_ws_url = (
                    'https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL')
        elif afip_ws == 'wsbfe':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://servicios1.afip.gov.ar/wsbfev1/service.asmx?WSDL')
            else:
                afip_ws_url = (
                    'https://wswhomo.afip.gov.ar/wsbfev1/service.asmx?WSDL')
        elif afip_ws == 'wsmtxca':
            raise UserError(_('AFIP WS %s Not implemented yet') % afip_ws)
            # if environment_type == 'production':
            #     afip_ws_url = (
            #         'https://serviciosjava.afip.gob.ar/wsmtxca/services/'
            #         'MTXCAService')
            # else:
            #     afip_ws_url = (
            #         'https://fwshomo.afip.gov.ar/wsmtxca/services/'
            #         'MTXCAService')
        elif afip_ws == 'wscdc':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://servicios1.afip.gov.ar/WSCDC/service.asmx?WSDL')
            else:
                afip_ws_url = (
                    'https://wswhomo.afip.gov.ar/WSCDC/service.asmx?WSDL')
        return afip_ws_url
