from odoo import api, fields, models
from odoo.tools import formatLang


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
        NO lo hacemos para el cambio de fiscal_position_id porque el onchange de fiscal_position_id implementado en sale_ux ya recomputa todos los taxes
        """
        for move in self.filtered(
            lambda x: x.is_sale_document(include_receipts=True) and x.perceptions_fiscal_positon and x.state == "draft"
        ):
            fp_tax_groups = move.fiscal_position_id.l10n_ar_tax_ids.filtered(
                lambda x: x.tax_type == "perception"
            ).mapped("default_tax_id.tax_group_id")
            new_taxes = move.fiscal_position_id._l10n_ar_add_taxes(
                move.partner_id, move.company_id, move.date, "perception"
            )
            # Solo queremos que se recomputen los impuestos en facturas de cliente/proveedor
            for line in move.filtered(lambda x: not x.reversed_entry_id).invoice_line_ids:
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

    def button_draft(self):
        """Ticket 119846.

        En los asientos de pago con retenciones AR las líneas de retención (con
        ``tax_repartition_line_id``) y sus bases las arma a mano
        ``account.payment._prepare_move_withholding_lines``, con importes que el motor de
        impuestos estándar de Odoo NO puede reproducir: los calcula la lógica l10n_ar (escalas y
        acumulado de ganancias, mínimos) o los carga el operador. El caso testigo es la retención
        de IVA, un impuesto ``fixed`` con ``amount = 0`` cuyo importe ingresa el operador mirando
        el IVA de las facturas; ``compute_all`` devuelve 0 para ese impuesto.

        Al pasar a borrador, el sync dinámico del asiento (``_sync_tax_lines`` /
        ``_sync_unbalanced_lines``) se reactiva —solo corre sobre moves no posteados— y recompone
        las líneas desde la base: la retención ``fixed/0`` recomputa a 0, cae en el filtro de
        importe cero de ``account.tax._prepare_tax_lines``, se descarta, y el asiento queda
        desbalanceado, forzando una "Automatic Balancing Line". No alcanza con preservar importes
        (``round_from_tax_lines``): el importe manual no es derivable del cómputo del impuesto, así
        que el motor no puede representarlo.

        Posteado no rompe porque ambos manejadores saltean ``state == 'posted'``. Replicamos eso
        en la transición a borrador: con ``skip_invoice_sync`` salteamos el recompute dinámico solo
        para los moves de pago con retenciones. Esas líneas las gobierna
        ``account.payment._synchronize_to_moves``, que las reconstruye ante cualquier edición
        posterior del pago.
        """
        wth_moves = self.filtered(lambda m: m.move_type == "entry" and m.origin_payment_id.l10n_ar_withholding_line_ids)
        if wth_moves:
            super(AccountMove, wth_moves.with_context(skip_invoice_sync=True)).button_draft()
        return super(AccountMove, self - wth_moves).button_draft()

    # -------------------------------------------------------------------------
    # Régimen de Transparencia Fiscal (Ley 27.743) — Percepciones de IIBB
    # -------------------------------------------------------------------------
    # Reutilizamos el cuadro de transparencia fiscal nacional ya existente en
    # l10n_ar (`_l10n_ar_get_invoice_custom_tax_summary_for_report`, que arma las
    # líneas de IVA Contenido / Otros Impuestos Nacionales) y le agregamos, a
    # continuación, una línea por cada percepción de Ingresos Brutos discriminada
    # por jurisdicción, según las resoluciones provinciales de transparencia
    # fiscal a consumidor final (ATER 128/2026 ER, AGIP 169/2026 CABA,
    # ARECH 468/2026 Chubut).
    #
    # La leyenda de cada percepción es la ETIQUETA del impuesto (`invoice_label`,
    # editable; default por jurisdicción en `account_chart_template._add_wh_taxes`)
    # más la alícuota, salvo Chubut que por norma informa solo la leyenda.

    # Jurisdicciones que informan solo la leyenda, sin alícuota (por norma).
    _L10N_AR_IIBB_TRANSPARENCY_NO_ALIQUOT = ("U",)

    def _l10n_ar_get_invoice_custom_tax_summary_for_report(self):
        """Extiende el cuadro de Transparencia Fiscal agregando una línea por cada
        percepción de Ingresos Brutos (tributo ARCA 07), a continuación del IVA.
        La leyenda es la etiqueta del impuesto (`invoice_label`) más la alícuota."""
        results = super()._l10n_ar_get_invoice_custom_tax_summary_for_report()
        # Mismo alcance que el régimen nacional: solo Facturas B (códigos 6/7/8).
        if self.l10n_latam_document_type_id.code not in ("6", "7", "8"):
            return results

        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()
        AccountTax = self.env["account.tax"]

        def grouping_function(_base_line, tax_data):
            if not tax_data:
                return None
            tax = tax_data["tax"]
            if tax.tax_group_id.l10n_ar_tribute_afip_code != "07":
                return None
            return {"tax_id": tax.id}

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue
            # Por defecto no informamos percepciones sin importe.
            # TODO: contemplar la exención de Chubut (ARECH 468/2026), que exige
            # informar "EXENTO DE ISIB CHUBUT" aun cuando el importe sea cero.
            if self.currency_id.is_zero(values["tax_amount_currency"]):
                continue
            tax = AccountTax.browse(grouping_key["tax_id"])
            name = tax.invoice_label or tax.name
            if tax.l10n_ar_state_code not in self._L10N_AR_IIBB_TRANSPARENCY_NO_ALIQUOT:
                name = "%s %g%%" % (name, tax.amount)
            results.append(
                {
                    "name": name,
                    "tax_amount_currency": values["tax_amount_currency"],
                    "formatted_tax_amount_currency": formatLang(self.env, values["tax_amount_currency"]),
                }
            )
        return results

    def _l10n_ar_get_invoice_totals_for_report(self):
        """Las percepciones de IIBB ya se informan en el cuadro de Transparencia
        Fiscal, así que las excluimos del cuadro de totales para no duplicar la
        información (solo en Facturas B, donde se muestra dicho cuadro).

        Excluir un grupo no altera el total del comprobante: el helper estándar
        `_exclude_tax_groups_from_tax_totals_summary` funde el importe del impuesto
        en la base y lo descuenta del tax, dejando el total igual.

        Solo excluimos los grupos de IIBB que efectivamente se informan en el
        cuadro de Transparencia Fiscal (importe != 0). Los de importe 0 no se
        listan allí (ver `_l10n_ar_get_invoice_custom_tax_summary_for_report`),
        así que se dejan en el cuadro de totales: no hay duplicación y se
        mantiene el comportamiento estándar de Odoo."""
        tax_totals = super()._l10n_ar_get_invoice_totals_for_report()
        if self.l10n_latam_document_type_id.code not in ("6", "7", "8") or not tax_totals:
            return tax_totals

        amount_by_group = {}
        for subtotal in tax_totals["subtotals"]:
            for tax_group in subtotal["tax_groups"]:
                amount_by_group[tax_group["id"]] = (
                    amount_by_group.get(tax_group["id"], 0.0) + tax_group["tax_amount_currency"]
                )
        iibb_group_ids = (
            self.env["account.tax.group"]
            .browse(list(amount_by_group))
            .filtered(
                lambda g: g.l10n_ar_tribute_afip_code == "07" and not self.currency_id.is_zero(amount_by_group[g.id])
            )
            .ids
        )
        if iibb_group_ids:
            tax_totals = self.env["account.tax"]._exclude_tax_groups_from_tax_totals_summary(tax_totals, iibb_group_ids)
        return tax_totals
