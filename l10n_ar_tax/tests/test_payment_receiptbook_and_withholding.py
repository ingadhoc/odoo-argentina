from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestL10nArWithholdingArRi


class TestPaymentReceiptbookAndWithholding(TestL10nArWithholdingArRi):
    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.company_bank_journal = self.env["account.journal"].search(
            [("company_id", "=", self.company_ri.id), ("type", "=", "bank")], limit=1
        )

    def test_create_vendor_payment_with_receiptbook_and_withholdings(self):
        """1. Create vendor bill for CABA partner and post.
        2. Create IIBB CABA fiscal position for company '(AR) Responsable Inscripto (Unit Tests)' with CABA withholding tax.
        3. Create payment for vendor bill created on step 1.
        4. VALIDATION: draft payment move must not have name.
        5. VALIDATION: draft payment move must have receiptbook.
        6. Post payment created on step 3.
        7. VALIDATION: payment move must have Document Number without document type.
        8. VALIDATION: Document Type on payment move must be set.
        9. VALIDATION: validate payment move lines amounts.
        """
        # 1. Create vendor bill for CABA partner and post.
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.env.ref("l10n_ar_tax.res_partner_adhoc_caba").id,
                "move_type": "in_invoice",
                "company_id": self.company_ri.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.env.ref("product.product_product_16").id,
                            "quantity": 1,
                            "price_unit": 500000,
                        }
                    ),
                ],
                "invoice_date": self.today,
                "l10n_latam_document_number": "1-2",
            }
        )
        invoice.action_post()

        # 2. Create IIBB CABA fiscal position for company '(AR) Responsable Inscripto (Unit Tests)' with CABA withholding tax.
        fiscal_pos = self.env["account.fiscal.position"].create(
            {
                "name": "IIBB CABA",
                "l10n_ar_afip_responsibility_type_ids": [(6, 0, [self.env.ref("l10n_ar.res_IVARI").id])],
                "sequence": 10,
                "auto_apply": True,
                "country_id": self.env.ref("base.ar").id,
                "company_id": invoice.company_id.id,
                "state_ids": [(6, 0, [self.env.ref("base.state_ar_c").id])],
            }
        )
        self.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": fiscal_pos.id,
                "default_tax_id": self.tax_wth_test_1.id,
                "tax_type": "withholding",
            }
        )

        # 3. Create payment for vendor bill created on step 1.
        action_context = invoice.action_register_payment()["context"]
        vals = {
            "journal_id": self.company_bank_journal.id,
            "amount": invoice.amount_total,
            "date": self.today,
        }
        payment = self.env["account.payment"].with_context(**action_context).create(vals)

        # 4. VALIDATION: draft payment move must not have name.
        self.assertEqual(payment.move_id.name, False)

        # 5. VALIDATION: draft payment move must have receiptbook.
        self.assertNotEqual(payment.receiptbook_id.id, False)

        # 6. Post payment created on step 3.
        payment.action_post()

        # 7. VALIDATION: payment move must have Document Number without document type.
        self.assertEqual(payment.move_id.l10n_latam_document_number, "0001-00000001")

        # 8. VALIDATION: Document Type on payment move must be set.
        self.assertEqual(
            self.env.ref("account_payment_pro_receiptbook.dc_orden_pago_x").id,
            payment.move_id.l10n_latam_document_type_id.id,
        )

        # 9. VALIDATION: validate payment move lines amounts.
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                # Liquidity line:
                {"debit": 0.0, "credit": 605000.0, "amount_currency": -605000.0},
                # base line:
                {"debit": 0.0, "credit": 500000.0, "amount_currency": -500000.0},
                # withholding line:
                {"debit": 0.0, "credit": 50000.0, "amount_currency": -50000.0},
                # base line:
                {"debit": 500000.0, "credit": 0.0, "amount_currency": 500000.0},
                # Receivable line:
                {"debit": 655000.0, "credit": 0.0, "amount_currency": 655000.0},
            ],
        )
