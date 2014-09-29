# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
import base64
from M2Crypto import X509

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')


class l10n_ar_wsafip_keygen_config(osv.osv_memory):

    def _default_company(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id

    def update_data(self, cr, uid, ids, company_id, context=None):
        company = self.pool.get('res.company').browse(cr, uid, company_id)
        v = {
            'wsafip_country_id': company.country_id.id if company.country_id else None,
            'wsafip_state_id': company.state_id.id if company.state_id else None,
            'wsafip_city': company.city or None,
            'wsafip_cuit': company.partner_id.vat[2:] if company.partner_id.vat else None,
        }
        return {'value': v}

    def execute(self, cr, uid, ids, context=None):
        """
        """
        pairkey_obj = self.pool.get('crypto.pairkey')

        for wzr in self.read(cr, uid, ids):
            pk_id = pairkey_obj.create(
                cr, uid, {'name': wzr['wsafip_name']}, context=context)
            x509_name = X509.X509_Name()
            x509_name.C = wzr['wsafip_country_id'][1].encode('ascii', 'ignore')
            x509_name.ST = wzr['wsafip_state_id'][1].encode('ascii', 'ignore')
            x509_name.L = wzr['wsafip_city'].encode('ascii', 'ignore')
            x509_name.O = wzr['wsafip_company_id'][1].encode('ascii', 'ignore')
            x509_name.OU = wzr['wsafip_department'].encode('ascii', 'ignore')
            x509_name.serialNumber = 'CUIT %s' % wzr[
                'wsafip_cuit'].encode('ascii', 'ignore')
            x509_name.CN = wzr['wsafip_name'].encode('ascii', 'ignore')
            pairkey_obj.generate_keys(cr, uid, [pk_id], context=context)
            crt_ids = pairkey_obj.generate_certificate_request(
                cr, uid, [pk_id], x509_name, context=context)

    _name = 'l10n_ar_wsafip.keygen_config'
    _inherit = 'res.config.installer'
    _columns = {
        'wsafip_company_id': fields.many2one('res.company', 'Company', required=True),
        'wsafip_country_id': fields.many2one('res.country', 'Country', required=True),
        'wsafip_state_id': fields.many2one('res.country.state', 'State', required=True),
        'wsafip_city': fields.char('City', size=64, required=True),
        'wsafip_department': fields.char('Department', size=64, required=True),
        'wsafip_cuit': fields.char('CUIT', size=16, required=True),
        'wsafip_name': fields.char('Name', size=64, required=True),
    }
    _defaults = {
        'wsafip_company_id': _default_company,
        'wsafip_department': 'IT',
        'wsafip_name': 'AFIP Web Services',
    }


class l10n_ar_wsafip_loadcert_config(osv.osv_memory):

    def update_data(self, cr, uid, ids, certificate_id, context=None):
        v = {}
        if certificate_id:
            certificate = self.pool.get(
                'crypto.certificate').browse(cr, uid, certificate_id)
            v = {
                'wsafip_request_file': base64.encodestring(certificate.csr),
            }
        return {'value': v}

    def execute(self, cr, uid, ids, context=None):
        """
        """
        certificate_obj = self.pool.get('crypto.certificate')
        for wz in self.browse(cr, uid, ids, context=context):
            wz.wsafip_request_id.write(
                {'crt': base64.decodestring(wz.wsafip_response_file)})
            try:
                wz.wsafip_request_id.have_crt(can_raise=True)
            except X509.X509Error, e:
                if 'Expecting: CERTIFICATE' in e[0]:
                    raise osv.except_osv(_('Wrong Certificate file format'),
                                         _('Be sure you have BEGIN CERTIFICATE string in your first line.'))
                else:
                    raise osv.except_osv(_('Unknown error'),
                                         _('X509 return this message:\n %s') % e[0])

            wz.wsafip_request_id.write({'state': 'confirmed'})

    _name = 'l10n_ar_wsafip.loadcert_config'
    _inherit = 'res.config.installer'
    _columns = {
        'wsafip_request_id': fields.many2one('crypto.certificate', 'Certificate Request', required=True),
        'wsafip_request_file': fields.binary('Download Signed Certificate Request', readonly=True),
        'wsafip_request_filename': fields.char('Filename', readonly=True),
        'wsafip_response_file': fields.binary('Upload Certificate', required=True),
    }
    _defaults = {
        'wsafip_request_filename': 'request.csr',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
