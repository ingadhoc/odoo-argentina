from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends()
    def _compute_tax_totals(self):
        super()._compute_tax_totals()

        for move in self.filtered(lambda x: x.state == "posted"):
            base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()

            # Detectar si hay impuestos inactivos en las líneas de impuestos
            inactive_trl_ids = {
                t["tax_repartition_line_id"].id
                for t in _tax_lines
                if t["tax_repartition_line_id"] and not t["tax_repartition_line_id"].tax_id.active
            }
            if not inactive_trl_ids:
                continue

            move.tax_totals = self._replace_inactive_tax_amounts(move, _tax_lines, inactive_trl_ids)

    def _replace_inactive_tax_amounts(self, move, _tax_lines, inactive_trl_ids):
        tax_totals = move.tax_totals
        subtotal = tax_totals["subtotals"][0]
        tax_groups = subtotal["tax_groups"]

        # 1. Acumular valores por tax_group
        amounts_by_group = {}

        for t in _tax_lines:
            trl = t["tax_repartition_line_id"]
            if not trl or trl.id not in inactive_trl_ids:
                continue

            group_id = trl.tax_id.tax_group_id.id
            vals = amounts_by_group.setdefault(group_id, {"amount_currency": 0.0, "amount": 0.0})

            vals["amount_currency"] += t["amount_currency"]
            vals["amount"] += t["balance"]

        if not amounts_by_group:
            return tax_totals

        # 2.Reemplazar valores en los tax_groups
        for g in tax_groups:
            group_id = g["id"]
            if group_id in amounts_by_group:
                vals = amounts_by_group[group_id]
                g["tax_amount_currency"] = abs(vals["amount_currency"])
                g["tax_amount"] = abs(vals["amount"])

        # 3. Recalcular subtotales
        subtotal["tax_amount_currency"] = sum(g["tax_amount_currency"] for g in tax_groups)
        subtotal["tax_amount"] = sum(g["tax_amount"] for g in tax_groups)

        # 4. Recalcular totales principales
        tax_totals["tax_amount_currency"] = subtotal["tax_amount_currency"]
        tax_totals["tax_amount"] = subtotal["tax_amount"]
        tax_totals["total_amount_currency"] = tax_totals["base_amount_currency"] + subtotal["tax_amount_currency"]
        tax_totals["total_amount"] = tax_totals["base_amount"] + subtotal["tax_amount"]

        return tax_totals
