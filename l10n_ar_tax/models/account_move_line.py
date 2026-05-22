from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    withholding_id = fields.Many2one("l10n_ar.payment.withholding", compute="_compute_withholding")

    def _compute_withholding(self):
        for rec in self:
            if rec.tax_line_id and rec.payment_id:
                rec.withholding_id = rec.payment_id.l10n_ar_withholding_line_ids.filtered(
                    lambda x: x.tax_id == rec.tax_line_id
                )
            else:
                rec.withholding_id = False

    def _get_computed_taxes(self):
        taxes = super()._get_computed_taxes()
        move = self.move_id
        # heredamos este metodo y no map_tax de fiscal positions porque el metodo map_tax recibe solo taxes y no sabe
        # partner ni fecha y estos datos son necesarios para computar correctamente la alicuota
        if move.is_sale_document(include_receipts=True) and move.fiscal_position_id.l10n_ar_tax_ids:
            if move.move_type == "out_refund" and move.fiscal_position_id.l10n_ar_require_related_invoice:
                # Con l10n_ar_require_related_invoice: solo agrega percepción si hay factura relacionada
                # en el mismo mes.
                related = move._found_related_invoice()
                if (
                    related
                    and move.invoice_date
                    and related.invoice_date
                    and move.invoice_date.year == related.invoice_date.year
                    and move.invoice_date.month == related.invoice_date.month
                    and move.currency_id.is_zero(related.amount_total - move.amount_total)
                ):
                    taxes += move.fiscal_position_id._l10n_ar_add_taxes(
                        self.partner_id, self.company_id, related.date, "perception"
                    )
            else:
                date = move.date if not move.reversed_entry_id else move.reversed_entry_id.date
                taxes += move.fiscal_position_id._l10n_ar_add_taxes(
                    self.partner_id, self.company_id, date, "perception"
                )
        return taxes
