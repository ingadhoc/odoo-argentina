from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_ar_partner_vat = fields.Char(related="partner_id.l10n_ar_vat", string="CUIT del destinatario")

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
