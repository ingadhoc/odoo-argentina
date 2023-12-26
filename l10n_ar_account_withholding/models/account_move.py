from odoo import models


class AccountMove(models.Model):
    """ Heredamos todos los metodos que de alguna manera llamen a tax.compute_all y les pasamos la fecha"""
    _inherit = "account.move"

    def _get_tax_factor(self):
        tax_factor = super()._get_tax_factor()
        doc_letter = self.l10n_latam_document_type_id.l10n_ar_letter
        # if we receive B invoices, then we take out 21 of vat
        # this use of case if when company is except on vat for eg.
        if tax_factor == 1.0 and doc_letter == 'B':
            tax_factor = 1.0 / 1.21
        return tax_factor

    def _compute_tax_totals(self):
        """ Mandamos en contexto el invoice_date para cauclo de impuesto con partner aliquot"""
        invoices = self.filtered(lambda x: x.is_invoice(include_receipts=True))
        for invoice in invoices:
            invoice = invoice.with_context(invoice_date=invoice.invoice_date if not invoice.reversed_entry_id else invoice.reversed_entry_id.invoice_date)
            super(AccountMove, invoice)._compute_tax_totals()
        super(AccountMove, self - invoices)._compute_tax_totals()

    def _l10n_ar_get_invoice_totals_for_report(self):
        """ Mandamos en contexto el invoice_date para cauclo de impuesto con partner aliquot
        cuando imprimos el reporte de factura """
        self.ensure_one()
        return super(AccountMove, self.with_context(invoice_date=self.invoice_date))._l10n_ar_get_invoice_totals_for_report()
