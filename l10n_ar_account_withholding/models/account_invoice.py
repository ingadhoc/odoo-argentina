from odoo import models, api, fields


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def _get_tax_factor(self):
        tax_factor = super(AccountInvoice, self)._get_tax_factor()
        doc_letter = self.document_type_id.document_letter_id.name
        # if we receive B invoices, then we take out 21 of vat
        # this use of case if when company is except on vat for eg.
        if tax_factor == 1.0 and doc_letter == 'B':
            tax_factor = 1.0 / 1.21
        return tax_factor

    @api.multi
    def get_taxes_values(self):
        """
        Hacemos esto para disponer de fecha de factura y cia para calcular
        impuesto con código python (por ej. para ARBA).
        Aparentemente no se puede cambiar el contexto a cosas que se llaman
        desde un onchange (ver https://github.com/odoo/odoo/issues/7472)
        entonces usamos este artilugio
        """
        date_invoice = self.date_invoice or fields.Date.context_today(self)
        # hacemos try porque al llamarse desde acciones de servidor da error
        try:
            self.env.context.date_invoice = date_invoice
            self.env.context.invoice_company = self.company_id
        except Exception:
            pass
        return super(AccountInvoice, self).get_taxes_values()


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.one
    def _compute_price(self):
        # ver nota en get_taxes_values
        invoice = self.invoice_id
        date_invoice = invoice.date_invoice or fields.Date.context_today(self)
        # hacemos try porque al llamarse desde acciones de servidor da error
        try:
            self.env.context.date_invoice = date_invoice
            self.env.context.invoice_company = self.company_id
        except Exception:
            pass
        return super(AccountInvoiceLine, self)._compute_price()
