from odoo import api, fields, models


class AccountMove(models.Model):
    """Heredamos todos los metodos que de alguna manera llamen a tax.compute_all y les pasamos la fecha"""

    _inherit = "account.move"

    perceptions_fiscal_positon = fields.Boolean(
        compute="_compute_perceptions_fiscal_position",
    )

    def _compute_perceptions_fiscal_position(self):
        """
        Compute if the fiscal position has perceptions.
        """
        for move in self:
            move.perceptions_fiscal_positon = bool(
                move.fiscal_position_id.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == "perception")
            )

    def _get_tax_factor(self):
        self.ensure_one()
        tax_factor = self.amount_total and (self.amount_untaxed / self.amount_total) or 1.0
        doc_letter = self.l10n_latam_document_type_id.l10n_ar_letter
        # if we receive B invoices, then we take out 21 of vat
        # this use of case if when company is except on vat for eg.
        if tax_factor == 1.0 and doc_letter == "B":
            tax_factor = 1.0 / 1.21
        return tax_factor

    def _post(self, soft=True):
        self.filtered(lambda x: x.perceptions_fiscal_positon and not x.invoice_date).mapped(
            "invoice_line_ids"
        )._compute_tax_ids()
        return super()._post(soft=soft)

    @api.onchange("invoice_date")
    def _l10n_ar_onchange_invoice_date(self):
        self.filtered(
            lambda x: x.is_sale_document(include_receipts=True) and x.perceptions_fiscal_positon and x.state == "draft"
        ).mapped("invoice_line_ids")._compute_tax_ids()

    def copy(self, default=None):
        """Re computamos las percepciones al duplicar una factura porque puede ser que la factura venga de otro periodo
        o por alguna razón las percepciones hayan cambiado
        """
        recs = super().copy(default=default)
        recs._l10n_ar_onchange_invoice_date()
        return recs
