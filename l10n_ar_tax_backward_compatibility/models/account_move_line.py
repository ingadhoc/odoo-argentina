from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_backward_withholding_payment = fields.Boolean()

    def get_and_verify_tax_alicuot(self):
        self.ensure_one()
        # if self.is_backward_withholding_payment:
        if not self.tax_line_id.amount:
            partner_field = (
                self.partner_id.l10n_ar_partner_perception_ids
                if self.move_id.is_invoice()
                else self.partner_id.l10n_ar_partner_tax_ids
            )
            partner_tax = partner_field.filtered(
                lambda x: x.company_id == self.company_id
                and x.tax_id.l10n_ar_state_id == self.tax_id.l10n_ar_state_id
                and (x.from_date <= self.date or not x.from_date)
                and (x.to_date <= self.date or not x.from_date)
            )
            if partner_tax:
                return partner_tax.tax_id.amount
        return super().get_and_verify_tax_alicuot()
