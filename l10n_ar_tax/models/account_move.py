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

    def write(self, vals):
        res = super().write(vals)
        # Si el invoice_date cambia, recomputamos las percepciones.
        # En Odoo 18+, cuando el guardado viene de un formulario (UI), los 'tax_ids' de las líneas
        # suelen estar presentes en los 'vals' (dentro de 'invoice_line_ids').
        # Si el usuario editó las líneas, no queremos re-ejecutar nuestra lógica de refresco automático.
        if "invoice_date" in vals and "invoice_line_ids" not in vals:
            self._l10n_ar_recompute_fiscal_position_taxes()
        return res

    @api.onchange("invoice_date", "commercial_partner_id")
    def _l10n_ar_recompute_fiscal_position_taxes(self):
        """Recalculamos las percepciones si cambiamos la fecha de la orden de venta o el commercial partner.
        IMPORTANTE: este metodo solo esta pensado para cambiar alicuota de MISMA fiscal position (por cambio en fecha o partner) pero no para cambiar los impuestos.
        Para ello nos basamos en los impuestos de la posicion fiscal, buscamos si hay impuestos existentes para los tax groups involucrados y los
        reemplazamos por los nuevos impuestos.
        NO lo hacemos para el cambio de fiscal_position_id porque el onchange de fiscal_position_id implementado en sale_ux ya recomputa todos los taxes.

        Para posiciones fiscales con l10n_ar_require_related_invoice=True:
        - En NC: solo aplica si es devolución total (mismo monto) en el mismo mes que la factura relacionada.
        - Si no cumple → elimina los impuestos de percepción de las líneas.
        """
        for move in self.filtered(
            lambda x: x.is_sale_document(include_receipts=True) and x.perceptions_fiscal_positon and x.state == "draft"
        ):
            fp_tax_groups = move.fiscal_position_id.l10n_ar_tax_ids.filtered(
                lambda x: x.tax_type == "perception"
            ).mapped("default_tax_id.tax_group_id")

            if move.move_type == "out_refund" and move.fiscal_position_id.l10n_ar_require_related_invoice:
                related = move._found_related_invoice()
                if (
                    related
                    and move.invoice_date
                    and related.invoice_date
                    and move.invoice_date.year == related.invoice_date.year
                    and move.invoice_date.month == related.invoice_date.month
                    and move.currency_id.is_zero(related.amount_total - move.amount_total)
                ):
                    new_taxes = move.fiscal_position_id._l10n_ar_add_taxes(
                        move.partner_id, move.company_id, related.date, "perception"
                    )
                    for line in move.invoice_line_ids:
                        to_unlink = line.tax_ids.filtered(lambda x: x.tax_group_id in fp_tax_groups)
                        if to_unlink._origin != new_taxes:
                            line.tax_ids = (line.tax_ids - to_unlink) | new_taxes
                else:
                    for line in move.invoice_line_ids:
                        to_unlink = line.tax_ids.filtered(lambda x: x.tax_group_id in fp_tax_groups)
                        if to_unlink:
                            line.tax_ids = line.tax_ids - to_unlink
            else:
                new_taxes = move.fiscal_position_id._l10n_ar_add_taxes(
                    move.partner_id, move.company_id, move.date, "perception"
                )
                for line in move.invoice_line_ids:
                    to_unlink = line.tax_ids.filtered(lambda x: x.tax_group_id in fp_tax_groups)
                    if to_unlink._origin != new_taxes:
                        line.tax_ids = (line.tax_ids - to_unlink) | new_taxes

    def copy(self, default=None):
        """Re computamos las percepciones al duplicar una factura porque puede ser que la factura venga de otro periodo
        o por alguna razón las percepciones hayan cambiado
        """
        recs = super().copy(default=default)
        recs._l10n_ar_recompute_fiscal_position_taxes()
        return recs
