# -*- coding: utf-8 -*-
from openerp.exceptions import Warning
from openerp import fields, models, api, _
from OpenSSL import crypto
from M2Crypto import BIO, SMIME, EVP
import base64
import logging
_logger = logging.getLogger(__name__)


class wsafip_certificate(models.Model):
    _name = "wsafip.certificate"
    _rec_name = "display_name"

    alias_id = fields.Many2one(
        'wsafip.certificate_alias',
        ondelete='cascade',
        string='Certificate Alias',
        required=True,
        )
    csr = fields.Text(
        'Request Certificate',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Certificate Request in PEM format.'
        )
    crt = fields.Text(
        'Certificate',
        readonly=True,
        states={
            'draft': [('readonly', False)], 'waiting': [('readonly', False)]},
        help='Certificate in PEM format.'
        )
    state = fields.Selection([
            ('draft', 'Draft'),
            ('waiting', 'Waiting'),
            ('confirmed', 'Confirmed'),
            ('cancel', 'Cancelled'),
        ],
        'State',
        select=True,
        readonly=True,
        default='draft',
        help='* The \'Draft\' state is used when a user is creating a new pair key. Warning: everybody can see the key.\
        \n* The \'Waiting\' state is used when a request has send to Certificate Authority and is waiting for response.\
        \n* The \'Confirmed\' state is used when a certificate is valid.\
        \n* The \'Canceled\' state is used when the key is not more used. You cant use this key again.')
    request_file = fields.Binary(
        'Download Signed Certificate Request',
        compute='get_request_file',
        readonly=True
        )
    request_filename = fields.Char(
        'Filename',
        readonly=True,
        compute='get_request_file',
        )
    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
        )

    @api.one
    @api.depends('create_date', 'alias_id.display_name')
    def _compute_display_name(self):
        names = [self.alias_id.display_name, self.create_date]
        self.display_name = ' / '.join(filter(None, names))

    @api.one
    @api.depends('csr')
    def get_request_file(self):
        if self.csr:
            self.request_filename = 'request.csr'
            self.request_file = base64.encodestring(
                self.csr)

    @api.multi
    def action_to_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def action_request(self):
        self.write({'state': 'waiting'})
        return True

    @api.multi
    def action_confirm(self):
        self.verify_crt()
        self.write({'state': 'confirmed'})
        return True

    @api.one
    def verify_crt(self):
        """
        Verify if certificate is well formed
        """
        crt = self.crt
        msg = False

        if not crt:
            msg = _('Invalid action! Please, set the certification string to continue.')
        certificate = self.get_certificate()
        if certificate is None:
            msg = _('Invalid action! Your certificate string is invalid. Check if you forgot the header CERTIFICATE or forgot/append end of lines.')
        if msg:
            raise Warning(msg)
        return True

    @api.multi
    def get_certificate(self):
        """
        Return Certificate object.
        """
        self.ensure_one()
        if self.crt:
            try:
                certificate = crypto.load_certificate(
                    crypto.FILETYPE_PEM, self.crt.encode('ascii'))
            except Exception, e:
                if 'Expecting: CERTIFICATE' in e[0]:
                    raise Warning(_(
                        'Wrong Certificate file format.\nBe sure you have BEGIN CERTIFICATE string in your first line.'))
                else:
                    raise Warning(_(
                    'Unknown error.\nX509 return this message:\n %s') % e[0])
        else:
            certificate = None
        return certificate

    @api.multi
    def smime(self, message):
        """
        Sign message in SMIME format.
        TODO migrate this method to not require M2Crypto
        """
        self.ensure_one()
        res = False
        if True:
            smime = SMIME.SMIME()
            ks = BIO.MemoryBuffer(self.alias_id.key.encode('ascii'))
            cs = BIO.MemoryBuffer(self.crt.encode('ascii'))
            bf = BIO.MemoryBuffer(str(message))
            out = BIO.MemoryBuffer()
            try:
                smime.load_key_bio(ks, cs)
            except EVP.EVPError:
                raise Warning(_(
                    'Error in Key and Certificate strings! Please check if private key and certificate are in ASCII PEM format.'))
            sbf = smime.sign(bf)
            smime.write(out, sbf)
            res = out.read()
        else:
            raise Warning(_(
                'This certificate is not ready to sign any message! Please set a certificate to continue. You must send your certification request to a authoritative certificator to get one, or execute a self sign certification'))
        return res
