# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning
import logging
import base64
from M2Crypto import X509

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')


class l10n_ar_wsafip_keygen_config(models.TransientModel):

    _name = 'l10n_ar_wsafip.keygen_config'
    _inherit = 'res.config.installer'

    wsafip_company = fields.Char(
        'Company Name', required=True
        )
    wsafip_company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env[
            'res.company']._company_default_get('l10n_ar_wsafip.keygen_config')
        )
    wsafip_country_id = fields.Many2one(
        'res.country', 'Country', required=True
        )
    wsafip_state_id = fields.Many2one(
        'res.country.state', 'State', required=True
        )
    wsafip_city = fields.Char(
        'City', size=64, required=True
        )
    wsafip_department = fields.Char(
        'Department', size=64, required=True, default='IT',
        )
    wsafip_cuit = fields.Char(
        'CUIT', size=16, required=True
        )
    wsafip_name = fields.Char(
        'Name', size=64, required=True, default='AFIP Web Services',
        help='Just a name, you can leave it this way'
        )

    @api.onchange('wsafip_company')
    def change_wsafip_company(self):
        if self.wsafip_company:
            self.wsafip_name = 'AFIP Web Services - %s' % self.wsafip_company

    @api.onchange('wsafip_company_id')
    def change_company(self):
        if self.wsafip_company_id:
            self.wsafip_company = self.wsafip_company_id.name
            self.wsafip_country_id = self.wsafip_company_id.country_id.id
            self.wsafip_state_id = self.wsafip_company_id.state_id.id
            self.wsafip_city = self.wsafip_company_id.city
            if self.wsafip_company_id.partner_id.vat:
                self.wsafip_cuit = self.wsafip_company_id.partner_id.vat[2:]

    @api.multi
    def execute(self):
        """
        """
        self.ensure_one()

        pairkey = self.env['crypto.pairkey'].create({'name': self.wsafip_name})
        x509_name = X509.X509_Name()
        x509_name.C = self.wsafip_country_id.code.encode('ascii', 'ignore')
        x509_name.ST = self.wsafip_state_id.name.encode('ascii', 'ignore')
        x509_name.L = self.wsafip_city.encode('ascii', 'ignore')
        x509_name.O = self.wsafip_company.encode('ascii', 'ignore')
        x509_name.OU = self.wsafip_department.encode('ascii', 'ignore')
        x509_name.serialNumber = 'CUIT %s' % (
            self.wsafip_cuit.encode('ascii', 'ignore'))
        x509_name.CN = self.wsafip_name.encode('ascii', 'ignore')
        pairkey.generate_keys()
        pairkey.generate_certificate_request(x509_name)


class l10n_ar_wsafip_loadcert_config(models.TransientModel):

    _name = 'l10n_ar_wsafip.loadcert_config'
    _inherit = 'res.config.installer'

    wsafip_request_id = fields.Many2one(
        'crypto.certificate', 'Certificate Request', required=True)
    wsafip_request_file = fields.Binary(
        'Download Signed Certificate Request', readonly=True)
    wsafip_request_filename = fields.Char(
        'Filename', readonly=True, default='request.csr')
    wsafip_response_file = fields.Binary(
        'Upload Certificate', required=True)

    @api.onchange('wsafip_request_id')
    def change_certificate(self):
        if self.wsafip_request_id:
            self.wsafip_request_file = base64.encodestring(
                self.wsafip_request_id.csr)

    @api.multi
    def execute(self):
        """
        """
        self.ensure_one()
        self.wsafip_request_id.write(
            {'crt': base64.decodestring(self.wsafip_response_file)})
        try:
            self.wsafip_request_id.have_crt(can_raise=True)
        except X509.X509Error, e:
            if 'Expecting: CERTIFICATE' in e[0]:
                raise Warning(_(
                    'Wrong Certificate file format.\nBe sure you have BEGIN CERTIFICATE string in your first line.'))
            else:
                raise Warning(_(
                    'Unknown error.\nX509 return this message:\n %s') % e[0])

        self.wsafip_request_id.write({'state': 'confirmed'})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
