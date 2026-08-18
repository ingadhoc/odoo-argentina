from odoo import models


class L10nArPaymentWithholding(models.Model):
    _inherit = "l10n_ar.payment.withholding"

    def _compute_base_amount(self):
        """Neuquén evalúa el mínimo sujeto a retención de IIBB por comprobante: el mínimo
        (campo "Minimum Base" / ``l10n_ar_base_minimum_threshold``) se compara contra el
        neto de CADA factura, no contra la suma de las bases (Res. Gral. 276/DPR/17,
        art. 10).

        El cálculo nativo suma las bases de todas las facturas del pago en un único
        ``base_amount`` y compara ese total contra el mínimo. Para Neuquén quitamos de
        ``base_amount`` la contribución de las facturas cuya base imponible completa no
        supera el mínimo, de modo que solo se retenga sobre las que sí lo superan. Los
        pagos de una sola factura quedan idénticos al comportamiento nativo.

        La base imponible que se compara es el neto para impuestos ``iibb_untaxed`` (IVA
        discriminado) y el total para ``iibb_total`` (IVA no discriminado), en línea con
        cómo ``base_amount`` construye la base.
        """
        super()._compute_base_amount()
        neuquen = self.env.ref("base.state_ar_q", raise_if_not_found=False)
        if not neuquen:
            return
        for wth in self.filtered(lambda x: x.partner_type == "supplier" and x._l10n_ar_is_neuquen_iibb()):
            tax = wth._get_withholding_tax()
            threshold = tax.l10n_ar_base_minimum_threshold
            is_total = tax.l10n_ar_tax_type == "iibb_total"
            sign = -1.0 if wth.partner_type == "supplier" else 1.0
            excluded = 0.0
            for line in wth.payment_id.to_pay_move_line_ids._origin:
                invoice = line.move_id
                if not invoice or not invoice.is_invoice():
                    continue
                # Base imponible COMPLETA de la factura para comparar con el mínimo.
                invoice_base = abs(invoice.amount_total_signed if is_total else invoice.amount_untaxed_signed)
                if invoice_base > threshold:
                    continue
                # La factura no supera el mínimo: quitamos su aporte a base_amount (mismo
                # factor y signo con que _compute_selected_debt_untaxed lo sumó).
                factor = 1.0 if is_total else (invoice._get_tax_factor() or 1.0)
                excluded += line.amount_residual * factor * sign
            wth.base_amount -= excluded

    def _tax_compute_all_helper(self):
        """Para Neuquén: retención sobre la base ya calificada incluso en pagos parciales,
        y detalle del cálculo en ``ref`` (como ganancias).

        Tras ``_compute_base_amount``, ``base_amount`` contiene solo las facturas cuya
        base imponible supera el mínimo. En un pago parcial esa base es proporcional al
        importe pagado y puede quedar por debajo del mínimo, con lo que el gate de base
        nativo la anularía. Como la calificación ya se resolvió por comprobante, en
        Neuquén retenemos sobre esa base (prorrateada) en lugar de anularla — igual que
        hace ganancias con su lógica propia. Además, se completa ``ref`` con el cálculo
        del importe retenido (para IIBB el nativo lo deja vacío)."""
        tax_amount, tax_account_id, tax_repartition_line_id, ref = super()._tax_compute_all_helper()
        if not self._l10n_ar_is_neuquen_iibb():
            return tax_amount, tax_account_id, tax_repartition_line_id, ref
        tax = self._get_withholding_tax()
        # Intervención de pago parcial: el nativo anuló (tax_amount 0) habiendo base
        # calificada (>0) proveniente de facturas → retenemos prorrateado. Los adelantos
        # puros (sin factura) y el gate por monto de pago mantienen el comportamiento nativo.
        invoices = self.payment_id.to_pay_move_line_ids.move_id.filtered(lambda m: m.is_invoice())
        payment_gate_blocks = (
            tax.l10n_ar_payment_minimum_threshold
            and self.payment_id.to_pay_amount <= tax.l10n_ar_payment_minimum_threshold
        )
        if not tax_amount and invoices and self.base_amount and not payment_gate_blocks:
            taxes_res = tax.compute_all(
                self.base_amount,
                currency=self.payment_id.currency_id,
                quantity=1.0,
                product=False,
                partner=False,
                is_refund=False,
            )
            tax_amount = self.currency_id.round(taxes_res["total_included"] - taxes_res["total_excluded"])
            # Conservamos el gate de importe mínimo calculado.
            if tax.l10n_ar_minimum_threshold > tax_amount:
                tax_amount = 0.0
        # Detalle del cálculo en ref (solo cuando corresponde retener).
        if tax_amount:
            f = self.currency_id.format
            ref = f"{f(self.base_amount)} * {tax.amount}% = {f(tax_amount)}"
        return tax_amount, tax_account_id, tax_repartition_line_id, ref

    def _l10n_ar_is_neuquen_iibb(self):
        """True si la línea es una retención de IIBB (untaxed/total) de jurisdicción
        Neuquén con mínimo por base configurado."""
        self.ensure_one()
        neuquen = self.env.ref("base.state_ar_q", raise_if_not_found=False)
        tax = self._get_withholding_tax()
        return bool(
            neuquen
            and tax.l10n_ar_state_id == neuquen
            and tax.l10n_ar_base_minimum_threshold
            and tax.l10n_ar_tax_type in ("iibb_untaxed", "iibb_total")
        )
