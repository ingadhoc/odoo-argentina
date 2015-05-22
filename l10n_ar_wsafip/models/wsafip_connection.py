# -*- coding: utf-8 -*-
from openerp import fields, models, api
from random import randint
from openerp.exceptions import Warning
import xml.etree.ElementTree as ET
from dateutil.parser import parse as dateparse
from dateutil.tz import tzlocal
from datetime import datetime, timedelta
from openerp.tools.translate import _
from suds.client import Client
import suds
import logging
from M2Crypto.X509 import X509Error

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

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


class wsafip_connection(models.Model):

    _name = "wsafip.connection"

    name = fields.Char(
        'Name',
        required=True
        )
    partner_id = fields.Many2one(
        'res.partner',
        'Partner',
        required=True,
        )
    server_id = fields.Many2one(
        'wsafip.server',
        'Service Server',
        required=True,
        )
    logging_id = fields.Many2one(
        'wsafip.server',
        'Authorization Server',
        required=True,
        )
    certificate_id = fields.Many2one(
        'wsafip.certificate',
        'Certificate',
        domain=[('state', '=', 'confirmed')]
        )
    uniqueid = fields.Integer(
        'Unique ID',
        readonly=True
        )
    token = fields.Text(
        'Token',
        readonly=True
        )
    sign = fields.Text(
        'Sign',
        readonly=True
        )
    generationtime = fields.Datetime(
        'Generation Time',
        readonly=True
        )
    expirationtime = fields.Datetime(
        'Expiration Time',
        readonly=True
        )
    state = fields.Selection(
        compute='_get_state',
        string='Status',
        readonly=True,
        selection=[
         ('clockshifted', 'Clock shifted'),
         ('connected', 'Connected'),
         ('disconnected', 'Disconnected'),
         ('invalid', 'Invalid'),
        ],
        )
    batch_sequence_id = fields.Many2one(
        'ir.sequence',
        'Batch Sequence',
        readonly=False
        )

    @api.one
    @api.depends(
        'uniqueid', 'generationtime', 'expirationtime', 'token', 'sign'
        )
    def _get_state(self):
        if False in (
                self.uniqueid, self.generationtime,
                self.expirationtime, self.token, self.sign):
            _logger.info("Disconnected from AFIP.")
            state = 'disconnected'
        elif not dateparse(self.generationtime) - timedelta(0, 5) < datetime.now():
            _logger.warning("clockshifted. Server: %s, Now: %s" %
                            (str(dateparse(self.generationtime)),
                                str(datetime.now())))
            _logger.warning(
                "clockshifted. Please syncronize your host to a NTP server.")
            state = 'clockshifted'
        elif datetime.now() < dateparse(self.expirationtime):
            state = 'connected'
        else:
            _logger.info("Invalid Connection from AFIP.")
            state = 'invalid'
            # 'Invalid Partner' si el cuit del partner no es el mismo al de la
            # clave publica/privada.
        self.state = state

    @api.one
    def login(self):
        if self.state not in ['connected', 'clockshifted']:
            uniqueid = randint(_intmin, _intmax)
            generationtime = (
                datetime.now(tzlocal()) - timedelta(0, 60)).isoformat()
            expirationtime = (
                datetime.now(tzlocal()) + timedelta(0, 60)).isoformat()
            msg = _login_message.format(
                uniqueid=uniqueid - _intmin,
                generationtime=generationtime,
                expirationtime=expirationtime,
                service=self.server_id.code
            )

            if not self.certificate_id:
                raise Warning(_(
                    'No certificate configured on AFIP connection %s' % (
                        self.name)))
            msg = self.certificate_id.smime(msg)
            head, body, end = msg.split('\n\n')

            try:
                aaclient = Client(self.logging_id.url + '?WSDL')
                response = aaclient.service.loginCms(in0=body)
            except Exception, e:
                raise Warning(
                    _('Could not connect. This is the what we received: %s' % e))
            except:
                raise Warning(
                    _('AFIP Web Service unvailable. Check your access to internet or contact to your system administrator.'))

            T = ET.fromstring(response)

            auth_data = {
                'source': T.find('header/source').text,
                'destination': T.find('header/destination').text,
                'uniqueid': int(T.find('header/uniqueId').text) + _intmin,
                'generationtime': dateparse(
                    T.find('header/generationTime').text),
                'expirationtime': dateparse(
                    T.find('header/expirationTime').text),
                'token': T.find('credentials/token').text,
                'sign': T.find('credentials/sign').text,
            }

            del auth_data['source']
            del auth_data['destination']

            _logger.info("Successful Connection to AFIP.")
            self.write(auth_data)

    @api.one
    def get_auth(self):
        if self.partner_id.document_type_id.name != 'CUIT':
            raise Warning(
                _('Partner without CUIT! Please setup document type as CUIT in partner.'))
        return {
            'Token': self.token.encode('ascii'),
            'Sign': self.sign.encode('ascii'),
            'Cuit': self.partner_id.document_number,
        }

    @api.multi
    def do_login(self):
        self.ensure_one()
        try:
            self.login()
        except X509Error, m:
            raise Warning(
                _('Certificate Error. This is what we get:\n%s') % m)
        except suds.WebFault, e:
            raise Warning(
                _('Error doing login. This is what we get:\n%s') % e.message)
        except Exception, e:
            raise Warning(
                _('Unknown Error. This is what we get:\n%s') % e)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
