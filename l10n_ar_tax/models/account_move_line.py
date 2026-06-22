from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    def action_register_payment(self, ctx=None):
        to_pay_partners = self.mapped("move_id.commercial_partner_id") or self.mapped("partner_id")
        company_pay_pro = len(self.mapped("company_id").ids) == 1 and self.mapped("company_id").use_payment_pro
        payment_pro = self.env.context.get("force_payment_pro")

        # Payment pro con múltiples partners → wizard account.payment.register con retenciones
        if payment_pro is not False and (payment_pro or company_pay_pro) and len(to_pay_partners) > 1:
            to_pay_move_lines = self.filtered(
                lambda r: not r.reconciled and r.account_id.account_type in ["asset_receivable", "liability_payable"]
            )
            if not to_pay_move_lines:
                raise UserError(_("Nothing to be paid on selected entries"))
            return {
                "name": _("Register Payment"),
                "type": "ir.actions.act_window",
                "res_model": "account.payment.register",
                "view_mode": "form",
                "views": [[False, "form"]],
                "target": "new",
                "context": {
                    "active_model": "account.move.line",
                    "active_ids": to_pay_move_lines.ids,
                    "default_company_id": self.company_id.id,
                    "payment_pro": True,
                },
            }
        return super().action_register_payment(ctx=ctx)

    @api.model_create_multi
    def create(self, vals_list):
        # Force display_type='product' for Argentine withholdings to keep them editable
        rep_id_to_vals = defaultdict(list)
        for vals in vals_list:
            if vals.get("display_type") == "tax" and (rep_id := vals.get("tax_repartition_line_id")):
                rep_id_to_vals[rep_id].append(vals)

        if rep_id_to_vals:
            rep_lines = self.env["account.tax.repartition.line"].browse(rep_id_to_vals.keys())
            for rep_line in rep_lines.filtered(lambda r: r.tax_id.l10n_ar_withholding_payment_type):
                for vals in rep_id_to_vals[rep_line.id]:
                    vals["display_type"] = "product"

        return super().create(vals_list)
