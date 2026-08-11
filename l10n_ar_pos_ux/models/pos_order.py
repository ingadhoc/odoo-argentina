##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def _complete_values_from_session(self, session, values):
        """
        Sobrescribimos para asegurar que la fiscal position se calcule correctamente
        según el partner, no solo usando la fiscal position por defecto.
        """
        values = super()._complete_values_from_session(session, values)

        # Si hay un partner, obtenemos su fiscal position
        if values.get("partner_id"):
            partner = self.env["res.partner"].browse(values["partner_id"])
            if partner.exists():
                # Primero verificar si el partner tiene una fiscal position manual
                fiscal_position = partner.property_account_position_id

                # Si no tiene manual, buscar la automática
                if not fiscal_position:
                    fiscal_position = (
                        self.env["account.fiscal.position"]
                        .with_company(values.get("company_id") or session.config_id.company_id.id)
                        ._get_fiscal_position(partner)
                    )

                if fiscal_position:
                    values["fiscal_position_id"] = fiscal_position.id

        return values

    @api.model
    def _get_invoice_lines_values(self, line_values, pos_order_line):
        """
        Sobrescribimos para NO pasar tax_ids explícitamente cuando hay percepciones.
        Esto permite que account.move.line._get_computed_taxes() se ejecute y agregue
        las percepciones automáticamente.
        """
        result = super()._get_invoice_lines_values(line_values, pos_order_line)

        # Si la orden tiene posición fiscal con percepciones, NO pasamos los tax_ids
        # para permitir que el sistema los compute automáticamente
        if (
            pos_order_line.order_id.fiscal_position_id
            and pos_order_line.order_id.fiscal_position_id.l10n_ar_tax_ids.filtered(
                lambda x: x.tax_type == "perception"
            )
        ):
            # En lugar de pasar tax_ids explícitamente, no los pasamos para que
            # _compute_tax_ids() se ejecute y llame a _get_computed_taxes()
            # que agregará las percepciones
            result.pop("tax_ids", None)

        return result


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribimos para agregar las percepciones a las líneas cuando se crean.
        """
        lines = super().create(vals_list)

        # Agregar percepciones a cada línea creada
        for line in lines:
            line._add_perceptions_to_line()

        return lines

    def _add_perceptions_to_line(self):
        """
        Agrega las percepciones argentinas a una línea de POS según la posición fiscal
        y el partner de la orden.
        """
        self.ensure_one()

        # Solo procesar si hay partner y fiscal position con percepciones
        if not self.order_id.partner_id or not self.order_id.fiscal_position_id:
            return

        fiscal_position = self.order_id.fiscal_position_id

        # Verificar si la posición fiscal tiene percepciones configuradas
        if not fiscal_position.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == "perception"):
            return

        # Obtener las percepciones usando el método de l10n_ar
        perception_taxes = fiscal_position._l10n_ar_add_taxes(
            partner=self.order_id.partner_id,
            company=self.order_id.company_id,
            date=self.order_id.date_order,
            tax_type="perception",
        )

        # Si hay percepciones, agregarlas a los tax_ids de la línea
        if perception_taxes:
            # Mapear los impuestos base según la fiscal position
            base_taxes = fiscal_position.map_tax(self.tax_ids)
            # Combinar impuestos base + percepciones
            all_taxes = base_taxes | perception_taxes

            # Actualizar la línea con todos los impuestos (sin triggear onchange)
            super(PosOrderLine, self).write({"tax_ids": [(6, 0, all_taxes.ids)]})

            # Recalcular los montos con las percepciones incluidas
            amounts = self._compute_amount_line_all()
            if amounts:
                super(PosOrderLine, self).write(amounts)

    def write(self, vals):
        """
        Sobrescribimos para recalcular percepciones cuando cambian campos relevantes.
        """
        result = super().write(vals)

        # Si cambiaron campos que afectan las percepciones, recalcularlas
        # pero solo si NO estamos en medio de una actualización de tax_ids para evitar bucles
        if any(field in vals for field in ["product_id", "price_unit", "qty", "discount"]) and "tax_ids" not in vals:
            for line in self:
                # Solo recalcular si ya tiene una orden con fiscal position y percepciones
                if (
                    line.order_id.partner_id
                    and line.order_id.fiscal_position_id
                    and line.order_id.fiscal_position_id.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == "perception")
                ):
                    line._add_perceptions_to_line()

        return result
