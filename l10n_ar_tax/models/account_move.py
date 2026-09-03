from odoo import Command, api, fields, models


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
            lambda x: x.is_sale_document(include_receipts=True)
            and x.fiscal_position_id
            and x.perceptions_fiscal_positon
            and x.state == "draft"
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

    def action_post(self):
        """Las percepciones/otros impuestos AR ``fixed`` (Perc IVA, Decreto 1008/2001) llevan el
        importe tipeado a mano por el operador. Al generar una NC, ese importe a veces se copia tal
        cual de la factura sin invertirle el signo (a diferencia de un impuesto ``percent``, que sí
        se recalcula bien): la percepción queda del mismo lado (haber) en la factura y en la NC.

        Corregir esto ANTES de terminar de postear no alcanza: hay una cadena larga de overrides de
        ``_post`` (EDI, numeración de documento, etc. — más de 30 módulos instalados la tocan) y
        cualquiera de ellos puede volver a escribir las líneas después de nuestra corrección,
        pisándola. Además, mientras el documento sigue en borrador, el sync dinámico del asiento
        (ver el docstring de ``button_draft`` arriba) puede recomponer la línea de nuevo. Por eso
        corregimos DESPUÉS de que todo el posteo terminó: un move posteado ya no dispara ese sync
        (solo corre sobre moves no posteados), así que esto es lo último que toca el asiento.
        """
        posted = super().action_post()
        for move in self.filtered(lambda m: m.reversed_entry_id and m.state == "posted"):
            original_lines = move.reversed_entry_id.line_ids
            updates = {}
            move_delta = move_delta_currency = 0.0
            # Comparamos contra la linea original: si quedo el mismo signo es que no se invirtio.
            # Evita un doble-flip sobre los casos que el core ya resuelve bien solo.
            for line in move.line_ids.filtered(
                lambda l: l.tax_line_id.amount_type == "fixed" and l.tax_line_id.country_id.code == "AR"
            ):
                orig_line = original_lines.filtered(lambda l: l.tax_line_id == line.tax_line_id)[:1]
                if orig_line and orig_line.balance and line.balance and (orig_line.balance > 0) == (line.balance > 0):
                    updates[line.id] = {"balance": -line.balance, "amount_currency": -line.amount_currency}
                    move_delta += -2 * line.balance
                    move_delta_currency += -2 * line.amount_currency
            if not updates:
                continue
            # Compensamos la contrapartida (proveedores) para que el asiento siga balanceando.
            # Solo con una unica linea de payment_term: es el caso comun de una NC de proveedor.
            payment_term_line = move.line_ids.filtered(lambda l: l.display_type == "payment_term")
            if len(payment_term_line) == 1:
                updates[payment_term_line.id] = {
                    "balance": payment_term_line.balance - move_delta,
                    "amount_currency": payment_term_line.amount_currency - move_delta_currency,
                }
            # Todo en un unico write con skip_invoice_sync: account.move.line valida el balance
            # en cada escritura (invertir la percepcion sin la compensacion en la misma llamada
            # rompe el chequeo), y sin skip_invoice_sync el sync dinamico pisa la correccion.
            move.with_context(skip_invoice_sync=True).write(
                {"line_ids": [Command.update(line_id, vals) for line_id, vals in updates.items()]}
            )
        return posted
