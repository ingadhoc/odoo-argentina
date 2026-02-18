import logging

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


# pylint: disable=R8180
class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _install_l10n_ar_tax_demo(self, company):
        """Crea demo data mínima para testing de edición de pagos con retenciones.

        Casos cubiertos:
        - Pago sin amount (solo retenciones)
        - Pago con amount, retenciones y write-off
        """
        company.ensure_one()
        self = self.with_company(company)

        _logger.info("Creating l10n_ar_tax payment demo data for company: %s", company.name)

        today = fields.Date.today()

        demo_data = {
            "account.move": {
                # Factura de proveedor CABA para test de pago sin amount
                "demo_vendor_bill_caba_1": {
                    "partner_id": "l10n_ar_tax.res_partner_adhoc_caba",
                    "move_type": "in_invoice",
                    "company_id": company.id,
                    "invoice_date": today,
                    "l10n_latam_document_number": "0001-00000100",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": "product.product_product_16",
                                "quantity": 1,
                                "price_unit": 100000,
                            }
                        )
                    ],
                },
                # Factura de proveedor CABA para test de edición de pago
                "demo_vendor_bill_caba_2": {
                    "partner_id": "l10n_ar_tax.res_partner_adhoc_caba",
                    "move_type": "in_invoice",
                    "company_id": company.id,
                    "invoice_date": today,
                    "l10n_latam_document_number": "0001-00000101",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": "product.product_product_16",
                                "quantity": 1,
                                "price_unit": 200000,
                            }
                        )
                    ],
                },
            },
        }

        self.sudo().with_context(skip_pdf_attachment_generation=True)._load_data(demo_data)

        # Post invoices
        for xml_id in ["demo_vendor_bill_caba_1", "demo_vendor_bill_caba_2"]:
            invoice = self.ref(xml_id)
            if invoice.state == "draft":
                invoice.action_post()
                _logger.info("Posted invoice %s", xml_id)

        # Create payments (draft state para que los tests puedan modificarlos)
        bank_journal = self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "=", "bank")], limit=1
        )

        # Payment 1: sin amount (solo retenciones)
        invoice_1 = self.ref("demo_vendor_bill_caba_1")
        action_context_1 = invoice_1.action_register_payment()["context"]
        payment_1 = (
            self.env["account.payment"]
            .with_context(**action_context_1)
            .create(
                {
                    "journal_id": bank_journal.id,
                    "amount": 0.0,
                    "date": today,
                }
            )
        )
        self.env["ir.model.data"].create(
            {
                "name": "demo_payment_only_withholdings",
                "module": "l10n_ar_tax",
                "model": "account.payment",
                "res_id": payment_1.id,
            }
        )
        _logger.info("Created payment demo_payment_only_withholdings")

        # Payment 2: con amount para editar
        invoice_2 = self.ref("demo_vendor_bill_caba_2")
        action_context_2 = invoice_2.action_register_payment()["context"]
        payment_2 = (
            self.env["account.payment"]
            .with_context(**action_context_2)
            .create(
                {
                    "journal_id": bank_journal.id,
                    "amount": 150000,
                    "date": today,
                }
            )
        )
        self.env["ir.model.data"].create(
            {
                "name": "demo_payment_to_edit",
                "module": "l10n_ar_tax",
                "model": "account.payment",
                "res_id": payment_2.id,
            }
        )
        _logger.info("Created payment demo_payment_to_edit")
