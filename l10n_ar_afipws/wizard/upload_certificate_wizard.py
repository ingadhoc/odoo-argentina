##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models
import base64


class L10nArAfipwsUploadCertificate(models.TransientModel):
    _name = 'afipws.upload_certificate.wizard'

    @api.model
    def get_certificate(self):
        return self.env['afipws.certificate'].browse(
            self._context.get('active_id'))

    certificate_id = fields.Many2one(
        'afipws.certificate',
        required=True,
        readonly=True,
        default=get_certificate,
        ondelete='cascade',
    )
    certificate_file = fields.Binary(
        'Upload Certificate',
        required=True
    )

    @api.multi
    def action_confirm(self):
        """
        """
        self.ensure_one()
        self.certificate_id.write(
            {'crt': base64.decodestring(self.certificate_file)})
        self.certificate_id.action_confirm()
        return True
