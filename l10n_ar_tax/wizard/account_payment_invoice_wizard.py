from odoo import api, models


class AccountPaymentInvoiceWizard(models.TransientModel):
    _inherit = "account.payment.invoice.wizard"

    @api.onchange("product_id")
    def change_product(self):
        super().change_product()
        self._l10n_ar_set_perception_taxes()

    @api.onchange("invoice_date")
    def _onchange_invoice_date_l10n_ar_perceptions(self):
        self._l10n_ar_set_perception_taxes()

    def _l10n_ar_set_perception_taxes(self):
        """Ticket 128732. La NC/ND rápida del pago toma solo los impuestos del producto, y como la línea se crea
        con tax_ids explícitos no pasa por account.move.line._get_computed_taxes, que es donde la factura común
        suma las percepciones de la posición fiscal según padrón. Replicamos acá esa misma lógica: reemplazamos
        los impuestos de los grupos de percepción de la posición fiscal por los que correspondan al partner a la
        fecha del comprobante."""
        for rec in self.filtered(lambda x: x.payment_id.partner_type == "customer"):
            company = rec.company_id or rec.env.company
            partner = rec.payment_id.partner_id
            # misma resolución que account.move._compute_fiscal_position_id: la posición fiscal automática se evalúa
            # sobre la dirección de entrega del partner, que puede estar en otra jurisdicción que el partner
            delivery = rec.env["res.partner"].browse(partner.address_get(["delivery"])["delivery"])
            fiscal_position = (
                rec.env["account.fiscal.position"]
                .with_company(company)
                ._get_fiscal_position(partner, delivery=delivery)
            )
            fp_perceptions = fiscal_position.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == "perception")
            if not fp_perceptions:
                continue
            fp_tax_groups = fp_perceptions.mapped("default_tax_id.tax_group_id")
            new_taxes = fiscal_position._l10n_ar_add_taxes(partner, company, rec.invoice_date, "perception")
            rec.tax_ids = rec.tax_ids.filtered(lambda x: x.tax_group_id not in fp_tax_groups) | new_taxes
