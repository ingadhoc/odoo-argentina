from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPaymentReceiptbookAndWithholding(TestArWithholdingArRi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.company_bank_journal = cls.env["account.journal"].create(
            {
                "name": "Bank Journal Test",
                "code": "BNKT",
                "type": "bank",
                "bank_statements_source": "file_import",
                "company_id": cls.company_ri.id,
            }
        )

    def test_custom_accounting_rate_with_withholdings(self):
        """Test que al pagar una factura en moneda extranjera con retenciones y un
        accounting_rate personalizado, las líneas del asiento se calculan correctamente.

        Escenario: el usuario ajusta manualmente el accounting_rate (antes se hacía vía
        force_amount_company_currency). Se verifica que el ajuste de retenciones en
        _prepare_move_lines_per_type no produce un doble ajuste sobre liquidez y contrapartida.

        Expected behavior:
        - Liquidity line balance = amount * accounting_rate.
        - Counterpart line balance = amount_company + withholdings (para que el asiento cuadre).
        - Withholding lines mantienen su propio balance intacto.
        """
        # 1. Set up USD currency with a known rate (1 USD = 100 ARS)
        usd = self.other_currency  # already set up in TestArWithholdingArRi with rates

        # Create a bank journal in USD for the payment
        usd_bank_journal = self.env["account.journal"].create(
            {
                "name": "Bank USD Test",
                "type": "bank",
                "code": "BUSD",
                "company_id": self.company_ri.id,
                "currency_id": usd.id,
            }
        )

        # 2. Create a vendor bill in USD
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.env.ref("l10n_ar_tax.res_partner_adhoc_caba").id,
                "move_type": "in_invoice",
                "company_id": self.company_ri.id,
                "currency_id": usd.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.env.ref("product.product_product_16").id,
                            "quantity": 1,
                            "price_unit": 1000,
                        }
                    ),
                ],
                "invoice_date": self.today,
                "l10n_latam_document_number": "1-100",
            }
        )
        invoice.action_post()

        # 3. Create fiscal position with IIBB CABA withholding for this partner
        fiscal_pos = self.env["account.fiscal.position"].create(
            {
                "name": "IIBB CABA FC",
                "l10n_ar_afip_responsibility_type_ids": [(6, 0, [self.env.ref("l10n_ar.res_IVARI").id])],
                "sequence": 10,
                "auto_apply": True,
                "country_id": self.env.ref("base.ar").id,
                "company_id": self.company_ri.id,
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

        # 4. Create payment from the invoice
        action_context = invoice.action_register_payment()["context"]
        payment = (
            self.env["account.payment"]
            .with_context(**action_context)
            .create(
                {
                    "journal_id": usd_bank_journal.id,
                    "amount": invoice.amount_total,
                    "date": self.today,
                }
            )
        )

        # Verify withholdings were computed
        self.assertTrue(payment.l10n_ar_withholding_line_ids, "Withholdings should have been computed")

        # 5. Personalizar accounting_rate para simular que el usuario ajusta el tipo de cambio manualmente
        # (en el modelo anterior esto se hacía vía force_amount_company_currency).
        # Ajustamos el rate levemente para simular un redondeo.
        original_rate = payment.accounting_rate or 1.0
        custom_rate = original_rate * 0.9999  # diferencia mínima para simular redondeo
        payment.accounting_rate = custom_rate

        # amount_company_currency equivalente con el nuevo rate
        amount_company = payment.amount * (payment.accounting_rate or 1.0)
        # retenciones en C (ARS) para comparar con el balance del asiento
        withholding_balance_ars = sum(payment.l10n_ar_withholding_line_ids.mapped("amount"))

        # 6. Confirmar el pago para materializar las líneas del asiento
        payment.action_post()

        self.assertTrue(payment.move_id, "Payment should have a journal entry after posting")

        liquidity_line = payment.move_id.line_ids.filtered(lambda l: l.account_id == payment.outstanding_account_id)
        counterpart_line = payment.move_id.line_ids.filtered(lambda l: l.account_type == "liability_payable")
        withholding_tax_lines = payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id)

        # 7. VERIFICACIONES CRÍTICAS:
        # La línea de liquidez refleja el monto ARS calculado con el rate personalizado
        self.assertAlmostEqual(
            abs(liquidity_line.balance),
            amount_company,
            places=2,
            msg="Liquidity line balance debe igualar amount * accounting_rate.",
        )

        # La contrapartida (cuenta payable) debe igualar liquidez + retenciones (asiento cuadra)
        expected_counterpart = amount_company + withholding_balance_ars
        self.assertAlmostEqual(
            abs(counterpart_line.balance),
            expected_counterpart,
            places=2,
            msg="Counterpart line balance debe igualar liquidez + retenciones ARS " "(el asiento debe cerrar en cero).",
        )

        # Las líneas de retención deben tener el importe correcto en ARS
        total_withholding_balance = abs(sum(withholding_tax_lines.mapped("balance")))
        self.assertAlmostEqual(
            total_withholding_balance,
            withholding_balance_ars,
            places=2,
            msg="Withholding lines balance debe coincidir con el importe ARS de las retenciones.",
        )

    def test_foreign_currency_withholding_balance_precision(self):
        """Test that withholding lines in a foreign currency payment preserve the exact ARS balance
        without rounding errors caused by the USD → ARS roundtrip.

        Bug scenario: withholding lines were created with currency_id=USD and amount_currency
        rounded to USD precision. Then _inverse_amount_currency recalculated balance from the
        rounded USD amount, producing a different ARS balance (e.g. 84,894.75 → 60 USD → 84,900).

        Expected behavior:
        - Withholding line balance must be the exact ARS amount (no rounding loss).
        - No automatic balancing line should be needed for the rounding difference.
        - Withholding lines should use company currency (ARS) when payment is in foreign currency.
        """
        usd = self.other_currency

        usd_bank_journal = self.env["account.journal"].create(
            {
                "name": "Bank USD Test 2",
                "type": "bank",
                "code": "BUS2",
                "company_id": self.company_ri.id,
                "currency_id": usd.id,
            }
        )

        # Create vendor bill in USD
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.env.ref("l10n_ar_tax.res_partner_adhoc_caba").id,
                "move_type": "in_invoice",
                "company_id": self.company_ri.id,
                "currency_id": usd.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.env.ref("product.product_product_16").id,
                            "quantity": 1,
                            "price_unit": 500,
                        }
                    ),
                ],
                "invoice_date": self.today,
                "l10n_latam_document_number": "1-200",
            }
        )
        invoice.action_post()

        # Create fiscal position with withholding
        fiscal_pos = self.env["account.fiscal.position"].create(
            {
                "name": "IIBB CABA FC Rounding",
                "l10n_ar_afip_responsibility_type_ids": [(6, 0, [self.env.ref("l10n_ar.res_IVARI").id])],
                "sequence": 10,
                "auto_apply": True,
                "country_id": self.env.ref("base.ar").id,
                "company_id": self.company_ri.id,
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

        # Create payment WITHOUT force_amount_company_currency
        action_context = invoice.action_register_payment()["context"]
        payment = (
            self.env["account.payment"]
            .with_context(**action_context)
            .create(
                {
                    "journal_id": usd_bank_journal.id,
                    "amount": invoice.amount_total,
                    "date": self.today,
                }
            )
        )

        self.assertTrue(payment.l10n_ar_withholding_line_ids, "Withholdings should have been computed")
        withholding_amount = payment.withholdings_amount
        self.assertGreater(withholding_amount, 0)

        # Post the payment to generate the journal entry with move lines
        payment.action_post()

        self.assertTrue(payment.move_id, "Payment should have a journal entry after posting")

        withholding_tax_lines = payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id)

        # CRITICAL: the withholding balance must be exactly the ARS amount, not a rounded USD→ARS roundtrip
        total_withholding_balance = abs(sum(withholding_tax_lines.mapped("balance")))
        self.assertAlmostEqual(
            total_withholding_balance,
            withholding_amount,
            places=2,
            msg="Withholding balance must exactly match the computed ARS amount. "
            "Before the fix, _inverse_amount_currency would recalculate balance from "
            "a rounded USD amount, producing a different value.",
        )

        # Verify withholding lines use company currency (ARS) when payment is in foreign currency
        for wth_line in withholding_tax_lines:
            self.assertEqual(
                wth_line.currency_id,
                payment.company_id.currency_id,
                "Withholding move lines should use company currency (ARS) "
                "when the payment is in foreign currency to avoid rounding issues.",
            )

        # Verify no automatic balancing line was needed
        auto_balance_lines = payment.move_id.line_ids.filtered(
            lambda l: "Automatic Balancing" in (l.name or "") or "automatic balancing" in (l.name or "").lower()
        )
        self.assertFalse(
            auto_balance_lines,
            "No automatic balancing line should be needed when withholding "
            "balances are exact (no rounding loss from currency conversion).",
        )

    def test_create_vendor_payment_with_receiptbook_and_withholdings(self):
        """1. Create vendor bill for CABA partner and post.
        2. Create IIBB CABA fiscal position for company '(AR) Responsable Inscripto (Unit Tests)' with CABA withholding tax.
        3. Create payment for vendor bill created on step 1.
        4. VALIDATION: draft payment move must not have name.
        5. Post payment created on step 3.
        6. VALIDATION: validate payment move lines amounts.
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

        # 5. Post payment created on step 3.
        payment.action_post()

        # 6. VALIDATION: validate payment move lines amounts.
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

    def test_withholding_amounts(self):
        """Verify withholding amount precision under 'round_globally' rounding method.

        With price_unit=391683 and a 4.5% withholding tax, the exact amount is
        391683 * 0.045 = 17625.735. Under 'round_globally', this rounds to 17625.74.
        The test ensures the rounding method is respected and the resulting
        withholding line carries the correctly rounded amount.
        """
        company = self.company_ri
        previous_rounding_method = company.tax_calculation_rounding_method
        company.tax_calculation_rounding_method = "round_globally"
        try:
            # Create a vendor bill with a single line subject to 21% VAT
            in_invoice_wht = self.env["account.move"].create(
                {
                    "move_type": "in_invoice",
                    "company_id": company.id,
                    "invoice_date": self.today,
                    "partner_id": self.env.ref("l10n_ar_tax.res_partner_adhoc_caba").id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "price_unit": 391683,
                                "tax_ids": [Command.set(self.tax_21.ids)],
                            }
                        )
                    ],
                    "l10n_latam_document_number": "2-5",
                }
            )
            in_invoice_wht.action_post()

            # Set withholding tax rate to 4.5% (produces a non-trivial rounding case)
            self.tax_wth_test_1.write({"amount": 4.5})

            # Create fiscal position with withholding for CABA partner
            fiscal_pos = self.env["account.fiscal.position"].create(
                {
                    "name": "IIBB CABA Rounding",
                    "l10n_ar_afip_responsibility_type_ids": [(6, 0, [self.env.ref("l10n_ar.res_IVARI").id])],
                    "sequence": 10,
                    "auto_apply": True,
                    "country_id": self.env.ref("base.ar").id,
                    "company_id": company.id,
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

            # Create payment using register payment context
            action_context = in_invoice_wht.action_register_payment()["context"]
            vals = {
                "journal_id": self.company_bank_journal.id,
                "amount": in_invoice_wht.amount_total,
                "date": self.today,
            }
            payment = self.env["account.payment"].with_context(**action_context).create(vals)

            # In direct payment creation flow, amount must be net of withholdings to fully reconcile the invoice.
            payment.action_post()

            self.assertEqual(payment.company_id.tax_calculation_rounding_method, "round_globally")
            # 391683 * 21% = 82253.43 (VAT) -> total invoice: 473936.43
            # 391683 * 4.5% = 17625.735 -> rounded globally to 17625.74 (withholding)
            # net payment (liquidity): 473936.43 - 17625.74 = 456310.69
            self.assertEqual(payment.l10n_ar_withholding_line_ids.amount, 17625.74)
        finally:
            company.tax_calculation_rounding_method = previous_rounding_method
