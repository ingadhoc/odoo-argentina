from odoo import api, fields, models


class AccountMove(models.Model):
    """Heredamos todos los metodos que de alguna manera llamen a tax.compute_all y les pasamos la fecha"""

    _inherit = "account.move"

    perceptions_fiscal_positon = fields.Boolean(
        compute="_compute_perceptions_fiscal_position",
    )

    @api.depends(
        "fiscal_position_id",
        "fiscal_position_id.l10n_ar_tax_ids",
        "fiscal_position_id.l10n_ar_tax_ids.tax_type",
    )
    def _compute_perceptions_fiscal_position(self):
        """
        Compute if the fiscal position has perceptions.
        """
        for move in self:
            move.perceptions_fiscal_positon = bool(
                move.fiscal_position_id.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == "perception")
            )

    @api.depends("partner_id", "partner_shipping_id", "company_id")
    def _compute_fiscal_position_id(self):
        """Skip the fiscal position on journal entries (move_type='entry', e.g. payments): it is not
        used there and, when it carries perceptions, it only adds a misleading warning banner."""
        entries = self.filtered(lambda move: move.move_type == "entry")
        entries.fiscal_position_id = False
        super(AccountMove, self - entries)._compute_fiscal_position_id()

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
        # Disparamos el recompute en write y no en create: al momento del create todavía no se
        # computaron todos los campos del account.move (líneas, importes, etc.), por lo que
        # _l10n_ar_recompute_fiscal_position_taxes no se ejecutaría correctamente en el create.
        # Si el invoice_date cambia, recomputamos las percepciones.
        # En Odoo 18+, cuando el guardado viene de un formulario (UI), los 'tax_ids' de las líneas
        # suelen estar presentes en los 'vals' (dentro de 'invoice_line_ids').
        # Si el usuario editó las líneas, no queremos re-ejecutar nuestra lógica de refresco automático.
        if ("invoice_date" in vals and "invoice_line_ids" not in vals) or (
            "fiscal_position_id" in vals
            and self.env["account.fiscal.position"].browse(vals["fiscal_position_id"]).l10n_ar_require_related_invoice
        ):
            self._l10n_ar_recompute_fiscal_position_taxes()
        return res

    @api.onchange("invoice_date", "commercial_partner_id")
    def _l10n_ar_recompute_fiscal_position_taxes(self):
        """Recalculamos las percepciones si cambiamos la fecha de la orden de venta o el commercial partner.
        IMPORTANTE: este metodo solo esta pensado para cambiar alicuota de MISMA fiscal position (por cambio en fecha o partner) pero no para cambiar los impuestos.
        Para ello nos basamos en los impuestos de la posicion fiscal, buscamos si hay impuestos existentes para los tax groups involucrados y los
        reemplazamos por los nuevos impuestos.
        Por regla general NO lo hacemos para el cambio de fiscal_position_id porque el onchange de fiscal_position_id implementado en sale_ux ya recomputa todos los taxes.
        EXCEPCION: write() sí invoca este recompute cuando se cambia a una fiscal_position_id con l10n_ar_require_related_invoice=True, para reevaluar las percepciones según las reglas de NC con reversión que se describen abajo.

        Para posiciones fiscales con l10n_ar_require_related_invoice=True:
        - En NC: solo aplica si es devolución total (mismo monto) en el mismo mes que la factura relacionada.
        - Si no cumple → elimina los impuestos de percepción de las líneas.
        """
        for move in self.filtered(
            lambda x: x.is_sale_document(include_receipts=True)
            and x.fiscal_position_id
            and x.perceptions_fiscal_positon
            and x.state == "draft"
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
                    and move.currency_id.is_zero(abs(related.amount_untaxed) - abs(move.amount_untaxed))
                ):
                    new_taxes = move.fiscal_position_id._l10n_ar_add_taxes(
                        move.partner_id, move.company_id, related.date, "perception"
                    )
                    for line in move.invoice_line_ids:
                        to_unlink = line.tax_ids.filtered(lambda x: x.tax_group_id in fp_tax_groups)
                        if to_unlink._origin != new_taxes:
                            line.tax_ids = (line.tax_ids - to_unlink) | new_taxes
                elif move._l10n_ar_so_invoice_same_untaxed():
                    # Existe una factura vinculada en la orden de venta con el mismo importe sin
                    # impuestos: calculamos las percepciones normalmente (como si la posición fiscal
                    # no tuviera l10n_ar_require_related_invoice).
                    new_taxes = move.fiscal_position_id._l10n_ar_add_taxes(
                        move.partner_id, move.company_id, move.date, "perception"
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
                # Solo queremos que se recomputen los impuestos en facturas de cliente/proveedor
                for line in move.filtered(lambda x: not x.reversed_entry_id).invoice_line_ids:
                    to_unlink = line.tax_ids.filtered(lambda x: x.tax_group_id in fp_tax_groups)
                    if to_unlink._origin != new_taxes:
                        line.tax_ids = (line.tax_ids - to_unlink) | new_taxes

    def _l10n_ar_so_invoice_same_untaxed(self):
        """Factura(s) de cliente posteada(s) vinculada(s) a la(s) misma(s) orden(es) de venta de esta
        NC, con el mismo importe sin impuestos. Se usa para decidir si, pese a no cumplirse la
        condición de devolución total contra la factura original (reversed_entry_id), igual
        corresponde calcular las percepciones. Vacío si el módulo sale no está instalado.
        """
        self.ensure_one()
        if "sale_line_ids" not in self.env["account.move.line"]._fields:
            return self.env["account.move"]
        orders = self.invoice_line_ids.sale_line_ids.order_id
        return orders.invoice_ids.filtered(
            lambda m: (
                m.move_type == "out_invoice" and m.state == "posted" and m.amount_untaxed == abs(self.amount_untaxed)
            )
        )[:1]

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
