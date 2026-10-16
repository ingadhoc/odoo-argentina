from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import str2bool


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
        elif (
            "invoice_line_ids" in vals
            and not self.env.context.get("l10n_ar_skip_credit_note_rules")
            and self._l10n_ar_credit_note_perception_rules_enabled()
        ):
            # Editing the lines can turn a total credit note into a partial one. Only on line edits: internal writes
            # run inside the tax lines sync, and changing taxes there leaves the tax lines out of date.
            self.filtered(lambda x: x.move_type == "out_refund")._l10n_ar_recompute_fiscal_position_taxes()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        if self._l10n_ar_credit_note_perception_rules_enabled():
            moves.filtered(lambda x: x.move_type == "out_refund")._l10n_ar_recompute_fiscal_position_taxes()
        return moves

    @api.onchange("invoice_date", "commercial_partner_id")
    def _l10n_ar_recompute_fiscal_position_taxes(self):
        """Recalculamos las percepciones si cambiamos la fecha de la orden de venta o el commercial partner.
        IMPORTANTE: este metodo solo esta pensado para cambiar alicuota de MISMA fiscal position (por cambio en fecha o partner) pero no para cambiar los impuestos.
        Para ello nos basamos en los impuestos de la posicion fiscal, buscamos si hay impuestos existentes para los tax groups involucrados y los
        reemplazamos por los nuevos impuestos.
        NO lo hacemos para el cambio de fiscal_position_id porque el onchange de fiscal_position_id implementado en sale_ux ya recomputa todos los taxes.

        Si están activas las reglas de percepciones en NC (ver _l10n_ar_credit_note_perception_rules_enabled), en las NC
        de cliente se aplican además las reglas de cada jurisdicción (ver _l10n_ar_credit_note_allows_perception).
        """
        rules_enabled = self._l10n_ar_credit_note_perception_rules_enabled()
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
            if rules_enabled and move.move_type == "out_refund":
                move._l10n_ar_apply_credit_note_perception_rules(fp_tax_groups)

    def _l10n_ar_credit_note_perception_rules_enabled(self):
        """Feature flag: reglas de percepciones en NC por jurisdicción. Se activa a mano por base con el
        parámetro de sistema 'l10n_ar_tax.credit_note_perception_rules', y aplica a todas las compañías de la base.
        TODO: evaluar en 20 dejarlo global y sacar el parámetro.
        """
        return str2bool(
            self.env["ir.config_parameter"].sudo().get_param("l10n_ar_tax.credit_note_perception_rules", "False"),
            default=False,
        )

    def _l10n_ar_apply_credit_note_perception_rules(self, fp_tax_groups):
        """Ajusta las percepciones de AGIP y ARBA de una NC de cliente; las del resto de las jurisdicciones no se tocan.
        - Si la NC anula totalmente una factura, cada línea lleva las percepciones de AGIP y ARBA de la línea de la
          factura que anula, si la jurisdicción las admite (ver _l10n_ar_credit_note_allows_perception).
        - Si no, no lleva percepciones de AGIP ni de ARBA.
        """
        self.ensure_one()

        def is_restricted(tax):
            return tax.tax_group_id in fp_tax_groups and tax.l10n_ar_state_id.jurisdiction_code in ("901", "902")

        invoice = self._l10n_ar_get_total_refund_invoice()
        commands = []
        for line in self.invoice_line_ids:
            # Taken from the invoice line, not recomputed: it keeps manual changes and avoids querying the padron
            # webservices
            allowed = (
                self._l10n_ar_refunded_invoice_line(line, invoice)
                .tax_ids.filtered(is_restricted)
                .filtered(lambda x: self._l10n_ar_credit_note_allows_perception(x, invoice))
            )
            restricted = line.tax_ids.filtered(is_restricted)
            if restricted._origin == allowed:
                continue
            if self.id:
                commands.append(
                    Command.update(line.id, {"tax_ids": [Command.set((line.tax_ids - restricted | allowed).ids)]})
                )
            else:
                line.tax_ids = (line.tax_ids - restricted) | allowed
        if commands:
            # Write through the move so its tax lines follow the new line taxes, without running the rules again
            self.with_context(l10n_ar_skip_credit_note_rules=True).write({"invoice_line_ids": commands})

    def _l10n_ar_refunded_invoice_line(self, line, invoice):
        """Línea de 'invoice' que anula la línea 'line' de esta NC: la de la misma línea de pedido de venta, o si no
        la del mismo producto y descripción, o si no la del mismo producto. Vacío si no hay ninguna.
        """
        invoice_lines = invoice.invoice_line_ids
        if "sale_line_ids" in line._fields and line.sale_line_ids:
            if same_sale_line := invoice_lines.filtered(lambda x: x.sale_line_ids & line.sale_line_ids):
                return same_sale_line[:1]
        same_product = invoice_lines.filtered(lambda x: x.product_id == line.product_id)
        return same_product.filtered(lambda x: x.name == line.name)[:1] or same_product[:1]

    def _l10n_ar_credit_note_allows_perception(self, tax, invoice):
        """Indica si la percepción 'tax' de AGIP o ARBA corresponde en esta NC, que anula totalmente 'invoice'.
        - AGIP (CABA): hasta 2 períodos mensuales siguientes a la factura (R. 312/DGR/2012 art. 21).
        - ARBA: sin plazo (RN 320/B/2011 art. 2).
        """
        self.ensure_one()
        if tax.l10n_ar_state_id.jurisdiction_code == "901":
            refund_date = self.invoice_date or fields.Date.context_today(self)
            invoice_date = invoice.invoice_date or invoice.date
            months = (refund_date.year - invoice_date.year) * 12 + refund_date.month - invoice_date.month
            return months <= 2
        return True

    def _l10n_ar_get_total_refund_invoice(self):
        """Factura que esta NC anula totalmente (mismo importe sin impuestos): la factura revertida o, si la NC no
        viene de una reversión, una factura de la misma orden de venta.
        """
        self.ensure_one()
        if self.reversed_entry_id:
            return self.reversed_entry_id.filtered(
                lambda x: self.currency_id.is_zero(x.amount_untaxed - self.amount_untaxed)
            )
        return self._l10n_ar_so_invoice_same_untaxed()

    def _l10n_ar_so_invoice_same_untaxed(self):
        """Factura de cliente posteada vinculada a la(s) misma(s) orden(es) de venta de esta NC, con el mismo
        importe sin impuestos. Vacío si el módulo sale no está instalado.
        """
        self.ensure_one()
        if "sale_line_ids" not in self.env["account.move.line"]._fields:
            return self.env["account.move"]
        orders = self.invoice_line_ids.sale_line_ids.order_id
        return orders.invoice_ids.filtered(
            lambda m: m.move_type == "out_invoice"
            and m.state == "posted"
            and self.currency_id.is_zero(m.amount_untaxed - self.amount_untaxed)
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

    def _l10n_ar_manual_fixed_perception_lines(self):
        """Líneas de impuesto AR ``fixed`` de este comprobante, con importe cargado.

        Son las percepciones/otros impuestos AR (Perc IVA, Decreto 1008/2001) cuyo importe tipea a
        mano el operador: el ``amount`` del impuesto es un placeholder y el motor de impuestos no
        puede derivar el importe real. Ver ``action_l10n_ar_create_refund_with_perceptions``.
        """
        self.ensure_one()
        return self.line_ids.filtered(
            lambda line: line.tax_line_id.amount_type == "fixed"
            and line.tax_line_id.country_id.code == "AR"
            and line.balance
        )

    def action_l10n_ar_create_refund_with_perceptions(self):
        """Crea la nota de crédito de una factura con percepciones de importe manual.

        El problema que evita: al usar "Agregar nota de crédito", la percepción queda del mismo
        lado que en la factura en vez de invertirse -su importe no es derivable del cómputo del
        impuesto, así que la reversión lo copia tal cual-, y la NC le acredita al proveedor de más,
        por el doble del importe.

        Corregir eso después no funciona: en borrador cualquier guardado que incluya
        ``invoice_line_ids`` -y el cliente web las manda al guardar antes de confirmar- hace que
        ``_sync_tax_lines`` vuelva a derivar el signo desde la dirección del documento; y una vez
        confirmada, la reversión ya concilió la NC contra la factura y
        ``account.move.line._check_reconciliation`` bloquea modificar esas líneas.

        Por eso acá no revertimos: creamos la NC como un ``in_refund`` nuevo, con las mismas líneas
        y la percepción ya del lado que corresponde. Al no haber ``reversed_entry_id`` no hay copia
        con el signo mal ni conciliación automática, el asiento coincide con lo que calcula el
        motor de impuestos y la corrección se sostiene tanto en borrador como al confirmar.

        Contrapartida de no revertir: la NC no queda vinculada a la factura, así que hay que
        conciliarla a mano. Dejamos la referencia en ``ref`` para la trazabilidad.
        """
        self.ensure_one()
        # in_invoice y no is_purchase_document(): ese ultimo tambien da True para una NC, y crear
        # la NC de una NC no tiene sentido.
        if self.state != "posted" or self.move_type != "in_invoice":
            raise UserError(_("Esta acción solo aplica a facturas de proveedor confirmadas."))
        if not self._l10n_ar_manual_fixed_perception_lines():
            raise UserError(
                _(
                    "%s no tiene percepciones de importe manual, así que no hace falta esta acción: "
                    "use “Agregar nota de crédito”.",
                    self.display_name,
                )
            )

        refund = self.env["account.move"].create(
            {
                "move_type": "in_refund",
                "partner_id": self.partner_id.id,
                "journal_id": self.journal_id.id,
                "company_id": self.company_id.id,
                "currency_id": self.currency_id.id,
                "invoice_date": fields.Date.context_today(self),
                "fiscal_position_id": self.fiscal_position_id.id,
                "invoice_payment_term_id": self.invoice_payment_term_id.id,
                "ref": _("NC de: %s", self.name),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": line.product_id.id,
                            "name": line.name,
                            "quantity": line.quantity,
                            "price_unit": line.price_unit,
                            "discount": line.discount,
                            "account_id": line.account_id.id,
                            "tax_ids": [Command.set(line.tax_ids.ids)],
                        }
                    )
                    for line in self.invoice_line_ids
                ],
            }
        )

        # La NC nace con la percepcion en el valor de la formula (un placeholder); la dejamos con
        # el importe de la factura y el signo invertido, que es lo que el operador espera.
        updates = {}
        for original in self._l10n_ar_manual_fixed_perception_lines():
            line = refund.line_ids.filtered(lambda l: l.tax_line_id == original.tax_line_id)[:1]
            if line:
                updates[line.id] = {
                    "balance": -original.balance,
                    "amount_currency": -original.amount_currency,
                }
        if updates:
            refund.write({"line_ids": [Command.update(line_id, vals) for line_id, vals in updates.items()]})

        return {
            "type": "ir.actions.act_window",
            "name": _("Nota de crédito"),
            "res_model": "account.move",
            "res_id": refund.id,
            "view_mode": "form",
            "context": dict(self.env.context, default_move_type="in_refund"),
        }
