# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    l10n_ar_report_signature = fields.Image('Firma:', related='company_id.l10n_ar_report_signature', readonly=False)
    l10n_ar_report_signed_by = fields.Text('Aclaracion:', related='company_id.l10n_ar_report_signed_by', readonly=False)
    l10n_ar_invoice_report_ars_amount = fields.Boolean(related='company_id.l10n_ar_invoice_report_ars_amount', readonly=False)

    def clean_signature(self):
        self.l10n_ar_report_signature = False
        self.l10n_ar_report_signed_by = False
