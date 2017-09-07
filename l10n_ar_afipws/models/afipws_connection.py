# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AfipwsConnection(models.Model):

    _name = "afipws.connection"
    _description = "AFIP WS Connection"
    _rec_name = "afip_ws"
    _order = "expirationtime desc"

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
    )
    uniqueid = fields.Char(
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
            raise UserError(_('Webservice %s not supported') % self.afip_ws)
        self.afip_ws_url = afip_ws_url

    @api.model
    def get_afip_login_url(self, environment_type):
        if environment_type == 'production':
            afip_login_url = (
                'https://wsaa.afip.gov.ar/ws/services/LoginCms')
        else:
            afip_login_url = (
                'https://wsaahomo.afip.gov.ar/ws/services/LoginCms')
        return afip_login_url

    @api.model
    def get_afip_ws_url(self, afip_ws, environment_type):
        """
        Function to be inherited on each module that add a new webservice
        """
        _logger.info('Getting URL for afip ws %s on %s' % (
            afip_ws, environment_type))
        return False

    @api.multi
    def check_afip_ws(self, afip_ws):
        # TODO tal vez cambiar nombre cuando veamos si devuelve otra cosa
        self.ensure_one()
        if self.afip_ws != afip_ws:
            raise UserError(_(
                'This method is for %s connections and you call it from an'
                ' %s connection') % (
                afip_ws, self.afip_ws))

    @api.multi
    def connect(self):
        """
        Method to be called
        """
        self.ensure_one()
        _logger.info(
            'Getting connection to ws %s from libraries on '
            'connection id %s' % (self.afip_ws, self.id))
        ws = self._get_ws(self.afip_ws)
        if not ws:
            raise UserError(_('AFIP Webservice %s not implemented yet' % (
                self.afip_ws)))
        # TODO implementar cache y proxy
        # create the proxy and get the configuration system parameters:
        # cfg = self.pool.get('ir.config_parameter')
        # cache = cfg.get_param(cr, uid, 'pyafipws.cache', context=context)
        # proxy = cfg.get_param(cr, uid, 'pyafipws.proxy', context=context)
        wsdl = self.afip_ws_url + '?WSDL'
        # connect to the webservice and call to the test method
        ws.Conectar("", wsdl or "", "")
        cuit = self.company_id.cuit_required()
        ws.Cuit = cuit
        ws.Token = self.token.encode('ascii')
        ws.Sign = self.sign.encode('ascii')
        # TODO till this this PR is accepted
        ws.Obs = ''
        ws.Errores = []

        _logger.info(
            'Connection getted with url "%s", cuit "%s"' % (
                wsdl, ws.Cuit))
        return ws

    @api.model
    def _get_ws(self, afip_ws):
        """
        Method to be inherited
        """
        _logger.info('Getting ws %s from libraries ' % afip_ws)
        return False
