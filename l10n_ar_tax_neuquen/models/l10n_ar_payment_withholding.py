from odoo import models


class L10nArPaymentWithholding(models.Model):
    _inherit = "l10n_ar.payment.withholding"

    def _tax_compute_all_helper(self):
        """En Neuquén el mínimo sujeto a retención de IIBB se analiza sobre la base
        imponible (neto sin impuestos) del comprobante, no sobre el total con
        impuestos ni sobre el monto del pago (Res. Gral. 276/DPR/17, art. 10).

        El mínimo se carga en el campo "Minimum Base" (``l10n_ar_base_minimum_threshold``).
        El gate estándar de ese campo compara contra ``base_amount`` (que para
        ``iibb_total`` es el total con impuestos y en pagos parciales es el neto
        proporcional). Para Neuquén lo comparamos contra el neto total de la/s
        factura/s pagada/s: si no supera el mínimo, no corresponde retener.
        """
        tax_amount, tax_account_id, tax_repartition_line_id, ref = super()._tax_compute_all_helper()
        tax = self._get_withholding_tax()
        neuquen = self.env.ref("base.state_ar_q", raise_if_not_found=False)
        if tax_amount and neuquen and tax.l10n_ar_state_id == neuquen and tax.l10n_ar_base_minimum_threshold:
            invoices = self.payment_id.to_pay_move_line_ids.move_id.filtered(lambda m: m.is_invoice())
            invoice_untaxed = abs(sum(invoices.mapped("amount_untaxed_signed")))
            # Sin facturas (adelanto puro) invoice_untaxed es 0 y no bloqueamos.
            if invoices and invoice_untaxed <= tax.l10n_ar_base_minimum_threshold:
                return 0.0, tax_account_id, tax_repartition_line_id, False
        return tax_amount, tax_account_id, tax_repartition_line_id, ref
