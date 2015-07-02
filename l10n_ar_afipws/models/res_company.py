# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from dateutil.tz import tzlocal
from datetime import datetime, timedelta
from dateutil.parser import parse as dateparse
from random import randint
from suds.client import Client
import xml.etree.ElementTree as ET
import suds
from M2Crypto.X509 import X509Error
import logging
from openerp.exceptions import Warning
import openerp.tools as tools
import os

_logger = logging.getLogger(__name__)

_login_message = """\
<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
<header>
    <uniqueId>{uniqueid}</uniqueId>
    <generationTime>{generationtime}</generationTime>
    <expirationTime>{expirationtime}</expirationTime>
</header>
<service>{service}</service>
</loginTicketRequest>"""

_intmin = -2147483648
_intmax = 2147483647


class res_company(models.Model):

    _inherit = "res.company"

    alias_ids = fields.One2many(
        'afipws.certificate_alias',
        'company_id',
        'Aliases',
        )
    connection_ids = fields.One2many(
        'afipws.connection',
        'company_id',
        'Connections',
        readonly=True,
        )

    @api.model
    def _get_environment_type(self):
        """
        Function to define homologation/production environment
        First it search for a paramter "afip.ws.env.type" if exists and:
        * is production --> production
        * is homologation --> homologation
        Else
        Search for 'server_mode' parameter on conf file. If that parameter is:
        * 'test' or 'develop' -->  homologation
        * other or no parameter -->  production
        """
        parameter_env_type = self.env[
            'ir.config_parameter'].get_param('afip.ws.env.type')
        if parameter_env_type == 'production':
            environment_type = 'production'
        elif parameter_env_type == 'homologation':
            environment_type = 'homologation'
        else:
            if tools.config.get('server_mode') in ('test', 'develop'):
                environment_type = 'homologation'
            else:
                environment_type = 'production'
        _logger.info(
            'Running arg electronic invoice on %s mode' % environment_type)
        return environment_type

    @api.multi
    def get_key_and_certificate(self, environment_type):
        """
        Funcion que busca para el environment_type definido,
        una clave y un certificado en los siguientes lugares y segun estas
        prioridades:
        * en el conf del server de odoo
        * en registros de esta misma clase
        """
        self.ensure_one
        pkey = False
        cert = False
        msg = False
        certificate = self.env['afipws.certificate'].search([
            ('alias_id.company_id', '=', self.id),
            ('alias_id.type', '=', environment_type),
            ('state', '=', 'confirmed'),
            ], limit=1)
        if certificate:
            pkey = certificate.alias_id.key
            cert = certificate.crt
            _logger.info('Using DB certificates')
        # not certificate on bd, we search on odo conf file
        else:
            msg = _('Not confirmed certificate for %s on company %s') % (
                environment_type, self.name)
            pkey_path = False
            cert_path = False
            if environment_type == 'production':
                pkey_path = tools.config.get('afip_prod_pkey_file')
                cert_path = tools.config.get('afip_prod_cert_file')
            else:
                pkey_path = tools.config.get('afip_homo_pkey_file')
                cert_path = tools.config.get('afip_homo_cert_file')
            if pkey_path and cert_path:
                try:
                    if os.path.isfile(pkey_path) and os.path.isfile(cert_path):
                        with open(pkey_path, "r") as pkey_file:
                            pkey = pkey_file.read()
                        with open(cert_path, "r") as cert_file:
                            cert = cert_file.read()
                    msg = 'Could not find %s or %s files' % (
                        pkey_path, cert_path)
                except:
                    msg = 'Could not read %s or %s files' % (
                        pkey_path, cert_path)
                else:
                    _logger.info('Using odoo conf certificates')
        if not pkey or not cert:
            raise Warning(msg)
        return (pkey, cert)

    @api.multi
    def get_connection(self, afip_ws):
        self.ensure_one()
        now = fields.Datetime.now()
        environment_type = self._get_environment_type()

        connection = self.connection_ids.search([
            ('type', '=', environment_type),
            ('generationtime', '<=', now),
            ('expirationtime', '>', now),
            ('afip_ws', '=', afip_ws),
            ], limit=1)
        if not connection:
            connection = self._create_connection(afip_ws, environment_type)
        return connection

    @api.multi
    def _create_connection(self, afip_ws, environment_type):
        """
        This function should be called from get_connection. Not to be used
        directyl
        """
        self.ensure_one()
        login_url = self.env['afipws.connection'].get_afip_login_url(
            environment_type)

        uniqueid = randint(_intmin, _intmax)
        generationtime = (
            datetime.now(tzlocal()) - timedelta(0, 60)).isoformat()
        expirationtime = (
            datetime.now(tzlocal()) + timedelta(0, 60)).isoformat()
        msg = _login_message.format(
            uniqueid=uniqueid - _intmin,
            generationtime=generationtime,
            expirationtime=expirationtime,
            service=afip_ws
        )
        pkey, cert = self.get_key_and_certificate(environment_type)
        msg = self.env['afipws.certificate'].smime(msg, pkey, cert)
        head, body, end = msg.split('\n\n')

        try:
            client = Client(login_url + '?WSDL')
            response = client.service.loginCms(in0=body)
        except Exception, e:
            raise Warning(
                _('Could not connect. This is the what we received: %s' % e))
        except:
            raise Warning(
                _('AFIP Web Service unvailable. Check your access to internet or contact to your system administrator.'))

        T = ET.fromstring(response)

        auth_data = {
            'uniqueid': int(T.find('header/uniqueId').text) + _intmin,
            'generationtime': dateparse(
                T.find('header/generationTime').text),
            'expirationtime': dateparse(
                T.find('header/expirationTime').text),
            'token': T.find('credentials/token').text,
            'sign': T.find('credentials/sign').text,
            'company_id': self.id,
            'afip_ws': afip_ws,
            'type': environment_type,
        }

        _logger.info("Successful Connection to AFIP.")
        return self.connection_ids.create(auth_data)
