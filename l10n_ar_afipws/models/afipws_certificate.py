##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import UserError
from odoo import fields, models, api, _
try:
    from OpenSSL import crypto
except ImportError:
    crypto = None
import base64
import logging
_logger = logging.getLogger(__name__)


class AfipwsCertificate(models.Model):
    _name = "afipws.certificate"
    _rec_name = "alias_id"

    alias_id = fields.Many2one(
        'afipws.certificate_alias',
        ondelete='cascade',
        string='Certificate Alias',
        required=True,
        auto_join=True,
        index=True,
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
            'draft': [('readonly', False)]},
        help='Certificate in PEM format.'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ],
        'State',
        index=True,
        readonly=True,
        default='draft',
        help="* The 'Draft' state is used when a user is creating a new pair "
        "key. Warning: everybody can see the key."
        "\n* The 'Confirmed' state is used when a certificate is valid."
        "\n* The 'Canceled' state is used when the key is not more used. You "
        "cant use this key again."
    )
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

    @api.multi
    @api.depends('csr')
    def get_request_file(self):
        for rec in self.filtered('csr'):
            rec.request_filename = 'request.csr'
            rec.request_file = base64.encodestring(self.csr.encode('utf-8'))

    @api.multi
    def action_to_draft(self):
        if self.alias_id.state != 'confirmed':
            raise UserError(_('Certificate Alias must be confirmed first!'))
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def action_confirm(self):
        self.verify_crt()
        self.write({'state': 'confirmed'})
        return True

    @api.multi
    def verify_crt(self):
        """
        Verify if certificate is well formed
        """
        for rec in self:
            crt = rec.crt
            msg = False

            if not crt:
                msg = _(
                    'Invalid action! Please, set the certification string to '
                    'continue.')
            certificate = rec.get_certificate()
            if certificate is None:
                msg = _(
                    'Invalid action! Your certificate string is invalid. '
                    'Check if you forgot the header CERTIFICATE or forgot/ '
                    'append end of lines.')
            if msg:
                raise UserError(msg)
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
            except Exception as e:
                if 'Expecting: CERTIFICATE' in e[0]:
                    raise UserError(_(
                        'Wrong Certificate file format.\nBe sure you have '
                        'BEGIN CERTIFICATE string in your first line.'))
                else:
                    raise UserError(_(
                        'Unknown error.\nX509 return this message:\n %s') % (
                        e[0]))
        else:
            certificate = None
        return certificate
