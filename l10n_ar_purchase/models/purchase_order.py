from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _get_name_purchase_report(self, report_xml_id):
        """ Method similar to the '_get_name_invoice_report' of l10n_latam_invoice_document
        Basically it allows different localizations to define it's own report
        This method should actually go in a sale_ux module that later can be extended by different localizations
        Another option would be to use report_substitute module and setup a subsitution with a domain
        """
        self.ensure_one()
        if self.company_id.country_id.code == 'AR':
            if report_xml_id == 'purchase.report_purchasequotation_document':
                return 'l10n_ar_purchase.report_purchasequotation_document'
            else:
                return 'l10n_ar_purchase.report_purchaseorder_document'
        return report_xml_id
