# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ar_report_signature = fields.Image("Firma:", related="company_id.l10n_ar_report_signature", readonly=False)
    l10n_ar_report_signed_by = fields.Text("Aclaracion:", related="company_id.l10n_ar_report_signed_by", readonly=False)
    l10n_ar_invoice_report_ars_amount = fields.Boolean(
        related="company_id.l10n_ar_invoice_report_ars_amount", readonly=False
    )
    group_include_pending_receivable_documents = fields.Boolean(
        string="Mostrar comprobantes pendientes en Recibos de Clientes",
        implied_group="l10n_ar_ux.group_include_pending_receivable_documents",
        help="Si marca esta opción, cuando se imprima o envíe un Recibo de Clientes, se incluirá"
        " una sección con todos los Comprobantes abiertos, es decir, que tengan algún saldo pendiente",
    )
    l10n_ar_afip_activity_id = fields.Many2one(
        related="company_id.l10n_ar_afip_activity_id",
        readonly=False,
    )

    def clean_signature(self):
        self.l10n_ar_report_signature = False
        self.l10n_ar_report_signed_by = False
