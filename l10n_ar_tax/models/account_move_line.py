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
        """
        Compute and return the taxes applicable to the account move line, with custom logic for Argentine localization.

        This method extends the base tax computation by:
        - Ensuring that VAT taxes are not removed for downpayment invoices when the move date changes.
        - Adding perception taxes based on the fiscal position, partner, company, and move date for sale documents.

        Returns:
            account.tax: The computed taxes for the account.move.line.
        """
        taxes = super()._get_computed_taxes()
        # Si es una factura de anticipo y se cambia la fecha al move_id no queremos que borre el impuesto de IVA en localización argentina
        if self.is_downpayment:
            taxes += self.tax_ids.filtered("tax_group_id.l10n_ar_vat_afip_code")
        # heredamos este metodo y no map_tax de fiscal positions porque el metod map_tax recibe solo taxes y no sabe
        # partner ni fecha y estos datos son necesarios para computar correctamente la alicuota
        if self.move_id.is_sale_document(include_receipts=True) and self.move_id.fiscal_position_id.l10n_ar_tax_ids:
            date = self.move_id.date
            taxes += self.move_id.fiscal_position_id._l10n_ar_add_taxes(
                self.partner_id, self.company_id, date, "perception"
            )
        return taxes

    def _compute_tax_ids(self):
        """
        Computes and assigns tax_ids for account.move.line.

        This method overrides the parent `_compute_tax_ids` to add custom logic for downpayment lines.
        For each line that is downpayment, it computes the applicable taxes using `_get_computed_taxes`
        and assigns them to `tax_ids`.
        """
        super()._compute_tax_ids()
        for line in self.filtered("is_downpayment"):
            line.tax_ids = line._get_computed_taxes()
