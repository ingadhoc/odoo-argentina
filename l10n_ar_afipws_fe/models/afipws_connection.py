# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api
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
            ('wsbfe', 'Bono Fiscal -con detalle- RG2557 (WSMTXCA)'),
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
                    'https://servicios1.afip.gov.ar/wsfev1/service.asmx')
            else:
                afip_ws_url = (
                    'https://wswhomo.afip.gov.ar/wsfev1/service.asmx')
        elif afip_ws == 'wsfex':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://servicios1.afip.gov.ar/wsfexv1/service.asmx')
            else:
                afip_ws_url = (
                    'https://wswhomo.afip.gov.ar/wsfexv1/service.asmx')
        elif afip_ws in ('wsmtxca', 'wsbfe'):
            raise Warning('AFIP WS %s Not implemented yet' % afip_ws)
        return afip_ws_url
