from odoo import Command, api, fields, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _install_l10n_ar_ux_demo(self, companies):
        """Crea data demo para argentina"""

        for company in companies.filtered(lambda x: x.country_code == "AR"):
            self = self.with_company(company)
            today = fields.Date.today()
            # Nota de crédito en USD
            credit_note_usd = (
                self.env["account.move"]
                .with_context(skip_pdf_attachment_generation=True, skip_readonly_check=True)
                .create(
                    {
                        "move_type": "out_refund",
                        "partner_id": self.env.ref("l10n_ar.res_partner_adhoc").id,
                        "currency_id": self.env.ref("base.USD").id,
                        "invoice_date": today,
                        "invoice_line_ids": [
                            Command.create({"product_id": self.env.ref("product.product_product_2").id, "quantity": 1})
                        ],
                        "company_id": company.id,
                    }
                )
            )
            if credit_note_usd.state == "draft":
                credit_note_usd.action_post()

            # Nota de crédito en ARS
            credit_note_ars = (
                self.env["account.move"]
                .with_context(skip_pdf_attachment_generation=True, skip_readonly_check=True)
                .create(
                    {
                        "move_type": "out_refund",
                        "partner_id": self.env.ref("l10n_ar.res_partner_gritti_agrimensura").id,
                        "currency_id": self.env.ref("base.ARS").id,
                        "invoice_date": today,
                        "invoice_line_ids": [
                            Command.create({"product_id": self.env.ref("product.product_product_2").id, "quantity": 1})
                        ],
                        "company_id": company.id,
                    }
                )
            )
            if credit_note_ars.state == "draft":
                credit_note_ars.action_post()

            # Facturas de proveedor en USD confirmadas para 3 partners
            doc_type = self.env.ref("l10n_ar.dc_c_f")  # Factura C
            for idx, partner_xmlid in enumerate(
                [
                    "l10n_ar.res_partner_gritti_agrimensura",
                    "l10n_ar.res_partner_adhoc",
                    "l10n_ar.partner_afip",
                ],
                start=25,
            ):
                invoice = (
                    self.env["account.move"]
                    .with_context(skip_pdf_attachment_generation=True, skip_readonly_check=True)
                    .create(
                        {
                            "move_type": "in_invoice",
                            "partner_id": self.env.ref(partner_xmlid).id,
                            "currency_id": self.env.ref("base.USD").id,
                            "invoice_date": today,
                            "l10n_latam_document_type_id": doc_type.id,
                            "l10n_latam_document_number": f"0001-{idx:08d}",
                            "invoice_line_ids": [
                                Command.create(
                                    {
                                        "product_id": self.env.ref("product.product_product_2").id,
                                        "quantity": 1,
                                        "price_unit": 100,
                                        "tax_ids": [
                                            Command.set(
                                                [
                                                    self.env.ref(
                                                        f"account.{company.id}_ri_tax_vat_no_corresponde_ventas"
                                                    ).id
                                                ]
                                            )
                                        ],
                                    }
                                )
                            ],
                            "company_id": company.id,
                        }
                    )
                )
                if invoice.state == "draft":
                    invoice.action_post()
