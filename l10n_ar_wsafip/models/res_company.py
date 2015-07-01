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

    production_certificate_id = fields.Many2one(
        'wsafip.certificate',
        'Certificate',
        domain=[('type', '=', 'production')]
        )
    homologation_certificate_id = fields.Many2one(
        'wsafip.certificate',
        'Certificate',
        domain=[('type', '=', 'homologation')]
        )
    connection_ids = fields.One2many(
        'wsafip.connection',
        'company_id',
        'Connections',
        )

    @api.model
    def _get_environment_type(self):
        """
        Function to be inherited in order to define homologation/production
        environment
        """
        # TODO implementar leer en las keys y devolver homo o prod
        return 'homologation'

    @api.model
    def _get_certificate(self, environment_type):
        if environment_type == 'production':
            certificate = self.production_certificate_id
        else:
            certificate = self.homologation_certificate_id

        if not certificate:
            raise Warning(_('Not certificate configured for %s') % (
                environment_type))

        return certificate

    @api.multi
    def get_connection(self, afip_ws):
        self.ensure_one()
        # TODO ver como verificar que el afip_ws este implementado
        now = datetime.now()
        environment_type = self._get_environment_type()

        connection = self.connection_ids.search([
            ('type', '=', environment_type),
            ('generationtime', '>=', now),
            ('expirationtime', '<', now),
            ('afip_ws', '=', afip_ws),
            ], limit=1)
        if not connection:
            connection = self.create_connection(afip_ws, environment_type)
        return connection

    @api.multi
    def _create_connection(self, afip_ws, environment_type):
        """
        This function should be called from get_connection. Not to be used
        directyl
        """
        self.ensure_one()
        login_url = self.connection_ids.get_afip_login_url()

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

        msg = self._get_certificate(environment_type).smime(msg)
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
