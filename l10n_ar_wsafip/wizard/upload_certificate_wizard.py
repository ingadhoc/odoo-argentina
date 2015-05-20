# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning
import base64
import logging

class l10n_ar_wsafip_upload_certificate(models.TransientModel):
    _name = 'wsafip.upload_certificate.wizard'

    @api.model
    def get_certificate(self):
        return self.env['wsafip.certificate'].browse(
            self._context.get('active_id'))

    certificate_id = fields.Many2one(
        'wsafip.certificate',
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
