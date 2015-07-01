# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from openerp.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)


class afipws_connection(models.Model):

    _name = "afipws.connection"
    _description = "AFIP WS Connection"
    _rec_name = "afip_ws"

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        )
    uniqueid = fields.Integer(
        'Unique ID',
        readonly=True,
        )
    token = fields.Text(
        'Token',
        readonly=True,
        )
    sign = fields.Text(
        'Sign',
        readonly=True,
        )
    generationtime = fields.Datetime(
        'Generation Time',
        readonly=True
        )
    expirationtime = fields.Datetime(
        'Expiration Time',
        readonly=True
        )
    batch_sequence_id = fields.Many2one(
        'ir.sequence',
        'Batch Sequence',
        readonly=False,
        )
    afip_login_url = fields.Char(
        'AFIP Login URL',
        compute='get_urls',
        )
    afip_ws_url = fields.Char(
        'AFIP WS URL',
        compute='get_urls',
        )
    type = fields.Selection(
        [('production', 'Production'), ('homologation', 'Homologation')],
        'Type',
        required=True,
        )
    afip_ws = fields.Selection(
        [],
        'AFIP WS',
        required=True,
        )

    @api.one
    @api.depends('type', 'afip_ws')
    def get_urls(self):
        self.afip_login_url = self.get_afip_login_url(self.type)

        afip_ws_url = self.get_afip_ws_url(self.afip_ws, self.type)
        if self.afip_ws and not afip_ws_url:
            raise Warning(_('Webservice %s not supported') % self.afip_ws)
        self.afip_ws_url = afip_ws_url

    @api.model
    def get_afip_login_url(self, environment_type):
        if environment_type == 'production':
            afip_login_url = 'https://wsaa.afip.gov.ar/ws/services/LoginCms'
        else:
            afip_login_url = 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms'
        return afip_login_url

    @api.model
    def get_afip_ws_url(self, afip_ws, environment_type):
        """
        Function to be inherited on each module that add a new webservice
        """
        self.ensure_one()
        return False

    @api.multi
    def check_afip_ws(self, afip_ws):
        # TODO tal vez cambiar nombre cuando veamos si devuelve otra cosa
        self.ensure_one()
        if self.afip_ws != afip_ws:
            raise Warning(_(
                'This method is for %s connections and you call it from an %s connection') % (
                afip_ws, self.afip_ws))

    @api.multi
    def connect(self):
        """
        Method to be called
        """
        self.ensure_one()
        ws = self._connect(self.afip_ws)
        if not ws:
            raise Warning(_('AFIP Webservice %s not implemented yet' % (
                self.afip_ws)))
        # TODO implementar cache y proxy
        # create the proxy and get the configuration system parameters:
        # cfg = self.pool.get('ir.config_parameter')
        # cache = cfg.get_param(cr, uid, 'pyafipws.cache', context=context)
        # proxy = cfg.get_param(cr, uid, 'pyafipws.proxy', context=context)
        wsdl = self.afip_ws_url+'?WSDL'
        # connect to the webservice and call to the test method
        ws.Conectar("", wsdl or "", "")
        ws.Cuit = self.company_id.partner_id.document_number
        ws.Token = self.token.encode('ascii')
        ws.Sign = self.sign.encode('ascii')
        return ws

    @api.model
    def _connect(self, afip_ws):
        """
        Method to be inherited
        """
        return False

    @api.multi
    def get_auth(self):
        self.ensure_one()
        if self.company_id.partner_id.document_type_id.name != 'CUIT':
            raise Warning(
                _('Company Partner without CUIT! Please setup document type as CUIT in partner.'))
        return {
            'Token': self.token.encode('ascii'),
            'Sign': self.sign.encode('ascii'),
            'Cuit': self.company_id.partner_id.document_number,
        }

    # @api.multi
    # def do_login(self):
    #     self.ensure_one()
    #     try:
    #         self.login()
    #     except X509Error, m:
    #         raise Warning(
    #             _('Certificate Error. This is what we get:\n%s') % m)
    #     except suds.WebFault, e:
    #         raise Warning(
    #             _('Error doing login. This is what we get:\n%s') % e.message)
    #     except Exception, e:
    #         raise Warning(
    #             _('Unknown Error. This is what we get:\n%s') % e)
    #     return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
