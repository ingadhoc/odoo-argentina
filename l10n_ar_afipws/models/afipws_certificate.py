# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp.exceptions import Warning
from openerp import fields, models, api, _
from OpenSSL import crypto
import base64
import logging
_logger = logging.getLogger(__name__)


class afipws_certificate(models.Model):
    _name = "afipws.certificate"
    _rec_name = "display_name"

    alias_id = fields.Many2one(
        'afipws.certificate_alias',
        ondelete='cascade',
        string='Certificate Alias',
        required=True,
        auto_join=True,
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
        _('Download Signed Certificate Request'),
        compute='get_request_file',
        readonly=True
        )
    request_filename = fields.Char(
        _('Filename'),
        readonly=True,
        compute='get_request_file',
        )
    display_name = fields.Char(
        string=_('Name'),
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
        if self.alias_id.state != 'confirmed':
            raise Warning(_('Certificate Alias must be confirmed first!'))
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
