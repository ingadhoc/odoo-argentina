from odoo import api, fields, models
from odoo.addons.l10n_ar.tools.partner_identifiers import AR_CUIT_AFIP_CODE
from stdnum.ar import cuit


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_ar_partner_vat = fields.Char(compute="_compute_l10n_ar_partner_vat", string="CUIT")

    @api.depends("partner_id.vat", "partner_id.l10n_ar_afip_code")
    def _compute_l10n_ar_partner_vat(self):
        # Same value as the removed res.partner.l10n_ar_vat: the compact CUIT, only when the partner is identified by it
        for rec in self:
            partner = rec.partner_id
            is_cuit = partner.vat and partner.l10n_ar_afip_code == AR_CUIT_AFIP_CODE
            rec.l10n_ar_partner_vat = cuit.compact(partner.vat) if is_cuit else False

    def _get_name_receipt_report(self, report_xml_id):
        """Method similar to the '_get_name_invoice_report' of l10n_latam_invoice_document
        Basically it allows different localizations to define it's own report
        This method should actually go in a sale_ux module that later can be extended by different localizations
        Another option would be to use report_substitute module and setup a subsitution with a domain
        """
        self.ensure_one()
        if self.company_id.country_id.code == "AR" and self.is_internal_transfer:
            return "l10n_ar_ux.report_account_transfer"
        return super()._get_name_receipt_report(report_xml_id)
