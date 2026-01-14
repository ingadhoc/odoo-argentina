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
        # heredamos este metodo y no map_tax de fiscal positions porque el metod map_tax recibe solo taxes y no sabe
        # partner ni fecha y estos datos son necesarios para computar correctamente la alicuota
        if self.move_id.is_sale_document(include_receipts=True) and self.move_id.fiscal_position_id.l10n_ar_tax_ids:
            date = self.move_id.date if not self.move_id.reversed_entry_id else self.move_id.reversed_entry_id.date
            taxes += self.move_id.fiscal_position_id._l10n_ar_add_taxes(
                self.partner_id, self.company_id, date, "perception"
            )
        return taxes
