# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from random import randint
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


class wsafip_connection(osv.osv):

    def _get_state(self, cr, uid, ids, fields_name, arg, context=None):
        r = {}
        for auth in self.browse(cr, uid, ids):
            if False in (auth.uniqueid, auth.generationtime, auth.expirationtime, auth.token, auth.sign):
                _logger.info("Disconnected from AFIP.")
                r[auth.id] = 'disconnected'
            elif not dateparse(auth.generationtime) - timedelta(0, 5) < datetime.now():
                _logger.warning("clockshifted. Server: %s, Now: %s" %
                                (str(dateparse(auth.generationtime)), str(datetime.now())))
                _logger.warning(
                    "clockshifted. Please syncronize your host to a NTP server.")
                r[auth.id] = 'clockshifted'
            elif datetime.now() < dateparse(auth.expirationtime):
                r[auth.id] = 'connected'
            else:
                _logger.info("Invalid Connection from AFIP.")
                r[auth.id] = 'invalid'
            # 'Invalid Partner' si el cuit del partner no es el mismo al de la clave publica/privada.
        return r

    _name = "wsafip.connection"
    _columns = {
        'name': fields.char('Name', size=64),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'server_id': fields.many2one('wsafip.server', 'Service Server'),
        'logging_id': fields.many2one('wsafip.server', 'Authorization Server'),
        'certificate': fields.many2one('crypto.certificate', 'Certificate Signer'),
        'uniqueid': fields.integer('Unique ID', readonly=True),
        'token': fields.text('Token', readonly=True),
        'sign': fields.text('Sign', readonly=True),
        'generationtime': fields.datetime('Generation Time', readonly=True),
        'expirationtime': fields.datetime('Expiration Time', readonly=True),
        'state': fields.function(_get_state,
                                 method=True,
                                 string='Status',
                                 type='selection',
                                 selection=[
                                     ('clockshifted', 'Clock shifted'),
                                     ('connected', 'Connected'),
                                     ('disconnected', 'Disconnected'),
                                     ('invalid', 'Invalid'),
                                 ],
                                 readonly=True),
        'batch_sequence_id': fields.many2one('ir.sequence', 'Batch Sequence', readonly=False),
    }

    _defaults = {
        'partner_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, [uid], c)[0].company_id.partner_id.id,
    }

    def login(self, cr, uid, ids, context=None):

        state = self._get_state(cr, uid, ids, None, None)

        for ws in self.browse(cr, uid, [_id for _id, _stat in state.items()
                                        if _stat not in ['connected', 'clockshifted']]):
            uniqueid = randint(_intmin, _intmax)
            generationtime = (
                datetime.now(tzlocal()) - timedelta(0, 60)).isoformat()
            expirationtime = (
                datetime.now(tzlocal()) + timedelta(0, 60)).isoformat()
            msg = _login_message.format(
                uniqueid=uniqueid - _intmin,
                generationtime=generationtime,
                expirationtime=expirationtime,
                service=ws.server_id.code
            )

            msg = ws.certificate.smime(msg)[ws.certificate.id]
            head, body, end = msg.split('\n\n')

            try:
                aaclient = Client(ws.logging_id.url + '?WSDL')
                response = aaclient.service.loginCms(in0=body)
            except:
                raise osv.except_osv(
                    _('AFIP Web Service unvailable'),
                    _('Check your access to internet or contact to your system administrator.'))

            T = ET.fromstring(response)

            auth_data = {
                'source': T.find('header/source').text,
                'destination': T.find('header/destination').text,
                'uniqueid': int(T.find('header/uniqueId').text) + _intmin,
                'generationtime': dateparse(T.find('header/generationTime').text),
                'expirationtime': dateparse(T.find('header/expirationTime').text),
                'token': T.find('credentials/token').text,
                'sign': T.find('credentials/sign').text,
            }

            del auth_data['source']
            del auth_data['destination']

            _logger.info("Successful Connection to AFIP.")
            self.write(cr, uid, ws.id, auth_data)

    def get_auth(self, cr, uid, ids, context=None):
        r = {}
        for auth in self.browse(cr, uid, ids):
            if auth.partner_id.document_type_id.name != 'CUIT':
                raise osv.except_osv(
                    _('Partner without CUIT'), _('Please setup document type as CUIT in partner.'))
            r[auth.id] = {
                'Token': auth.token.encode('ascii'),
                'Sign': auth.sign.encode('ascii'),
                'Cuit': auth.partner_id.document_number,
            }
        if len(ids) == 1:
            return r[ids[0]]
        else:
            return r

    def do_login(self, cr, uid, ids, context=None):
        try:
            self.login(cr, uid, ids)
        except X509Error, m:
            raise osv.except_osv(_('Certificate Error'), _(m))
        except suds.WebFault, e:
            raise osv.except_osv(_('Error doing login'), _("%s" % e.message))
        except Exception, e:
            raise osv.except_osv(_('Unknown Error'), _("%s" % e))
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
