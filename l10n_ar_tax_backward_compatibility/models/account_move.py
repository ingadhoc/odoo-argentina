from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends()
    def _compute_tax_totals(self):
        super()._compute_tax_totals()

        # tax_totals solo se llena en facturas: para el resto de los asientos el compute de
        # account deja None (se lee como False), así que un asiento que no es factura -el
        # asiento de un pago con retenciones, por ejemplo- no tiene nada que reemplazar.
        for move in self.filtered(lambda x: x.state == "posted" and x.is_invoice(include_receipts=True)):
            base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()

            # Grupos con algún impuesto inactivo. El reemplazo trabaja por grupo y no
            # por línea de impuesto: un grupo puede mezclar un impuesto archivado y el
            # vigente que lo reemplazó -pasa después de consolidar compañías-, y ahí el
            # total del grupo son las dos partes, no solo la archivada.
            inactive_group_ids = {
                t["tax_repartition_line_id"].tax_id.tax_group_id.id
                for t in _tax_lines
                if t["tax_repartition_line_id"] and not t["tax_repartition_line_id"].tax_id.active
            }
            if not inactive_group_ids:
                continue

            move.tax_totals = self._replace_inactive_tax_amounts(move, _tax_lines, inactive_group_ids)

    def _replace_inactive_tax_amounts(self, move, _tax_lines, inactive_group_ids):
        tax_totals = move.tax_totals
        subtotal = tax_totals["subtotals"][0]
        tax_groups = subtotal["tax_groups"]

        # 1. Acumular valores por tax_group, con todas sus líneas de impuesto
        amounts_by_group = {}

        for t in _tax_lines:
            trl = t["tax_repartition_line_id"]
            if not trl or trl.tax_id.tax_group_id.id not in inactive_group_ids:
                continue

            group_id = trl.tax_id.tax_group_id.id
            vals = amounts_by_group.setdefault(group_id, {"amount_currency": 0.0, "amount": 0.0})

            vals["amount_currency"] += t["amount_currency"]
            vals["amount"] += t["balance"]

        if not amounts_by_group:
            return tax_totals

        # Overrides manuales (account_invoice_tax.tax_override_data). Si el módulo
        # no está instalado el campo no existe, así que accedemos de forma segura.
        overrides = move.tax_override_data if "tax_override_data" in move._fields else False
        overrides = overrides or {}

        # 2.Reemplazar valores en los tax_groups. El widget expresa los importes con
        # el signo del documento, no en valor absoluto: un total que tiene que dar
        # negativo con abs() salía positivo.
        sign = move.direction_sign
        for g in tax_groups:
            group_id = g["id"]
            if group_id not in amounts_by_group:
                continue
            # Si algún impuesto del grupo tiene un override manual, lo respetamos:
            # super()._compute_tax_totals() ya dejó ese valor en el grupo, no lo
            # pisamos con el monto que sale de las líneas de impuesto.
            if any(str(tax_id) in overrides for tax_id in g.get("involved_tax_ids", [])):
                continue
            vals = amounts_by_group[group_id]
            g["tax_amount_currency"] = sign * vals["amount_currency"]
            g["tax_amount"] = sign * vals["amount"]

        # 3. Recalcular subtotales
        subtotal["tax_amount_currency"] = sum(g["tax_amount_currency"] for g in tax_groups)
        subtotal["tax_amount"] = sum(g["tax_amount"] for g in tax_groups)

        # 4. Recalcular totales principales
        tax_totals["tax_amount_currency"] = subtotal["tax_amount_currency"]
        tax_totals["tax_amount"] = subtotal["tax_amount"]
        tax_totals["total_amount_currency"] = tax_totals["base_amount_currency"] + subtotal["tax_amount_currency"]
        tax_totals["total_amount"] = tax_totals["base_amount"] + subtotal["tax_amount"]

        return tax_totals
