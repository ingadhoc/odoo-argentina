# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class afip_point_of_sale(models.Model):
    _inherit = 'afip.point_of_sale'

    afip_ws = fields.Selection([
        ('wsfe', 'Mercado interno -sin detalle- RG2485 (WSFEv1)'),
        ('wsfex', 'Exportación -con detalle- RG2758 (WSFEXv1)'),
        ('wsmtxca', 'Mercado interno -con detalle- RG2904 (WSMTXCA)'),
        ('wsbfe', 'Bono Fiscal -con detalle- RG2557 (WSMTXCA)'),
        ],
        'AFIP WS',
        )

    @api.multi
    def test_pyafipws_dummy(self):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento de
        infraestructura (FEDummy)
        """
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise Warning(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        ws.Dummy()
        title = _("AFIP service %s ") % afip_ws
        msg = "AppServerStatus: %s DbServerStatus: %s AuthServerStatus: %s"
        return {
            'type': 'ir.actions.act_window.message',
            'title': title,
            'message': msg % (
                ws.AppServerStatus,
                ws.DbServerStatus,
                ws.AuthServerStatus),
            }

    @api.multi
    def test_pyafipws_point_of_sales(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise Warning(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        ret = ws.ParamGetPtosVenta(sep=" ")
        msg = (_(" %s %s") % (
            '. '.join(ret), " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        return {
            'type': 'ir.actions.act_window.message',
            'title': _('Enabled Point Of Sales on AFIP'),
            'message': msg,
            }

    @api.multi
    def get_pyafipws_cuit_document_classes(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise Warning(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        ret = ws.FEParamGetTiposCbte(sep=" ")
        msg = (_(" %s %s") % (
            '. '.join(ret), " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        return {
            'type': 'ir.actions.act_window.message',
            'title': _('Authorized Document Clases on AFIP'),
            'message': msg,
            }
