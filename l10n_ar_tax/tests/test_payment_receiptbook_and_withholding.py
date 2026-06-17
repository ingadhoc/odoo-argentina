from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi


class TestPaymentReceiptbookAndWithholding(TestArWithholdingArRi):
    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.company_bank_journal = self.env["account.journal"].search(
            [("company_id", "=", self.company_ri.id), ("type", "=", "bank")], limit=1
        )

    def test_force_amount_company_currency_with_withholdings(self):
        """Test that when paying a foreign currency vendor bill with withholdings and a forced
        company currency amount, the journal entry lines are correctly computed.

        Bug scenario: when force_amount_company_currency is set, the withholding adjustment in
        l10n_ar_tax was double-adjusting the balance of liquidity and counterpart lines, because
        account_payment_pro had already set the correct forced balance.

        Expected behavior:
        - Liquidity line balance must equal the forced amount (not payment_total).
        - Counterpart line balance must equal the payment_total (to cancel the original debt).
        - Withholding lines keep their own balance untouched.
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
        withholding_amount = payment.withholdings_amount
        self.assertGreater(withholding_amount, 0, "Withholding amount should be positive")

        # 5. Set force_amount_company_currency to simulate the user forcing a rounded amount
        # The forced amount is slightly different from the computed conversion to simulate rounding adjustment
        normal_amount_company_currency = payment.amount_company_currency
        forced_amount = normal_amount_company_currency - 1  # simulate a small rounding difference
        payment.force_amount_company_currency = forced_amount

        # 6. Generate journal entry and post to materialize the move lines
        payment.action_post()

        self.assertTrue(payment.move_id, "Payment should have a journal entry after posting")

        liquidity_line = payment.move_id.line_ids.filtered(lambda l: l.account_id == payment.outstanding_account_id)
        counterpart_line = payment.move_id.line_ids.filtered(lambda l: l.account_type == "liability_payable")
        withholding_tax_lines = payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id)

        # 7. CRITICAL ASSERTIONS:
        # The liquidity line balance must reflect the forced amount, NOT the payment_total
        self.assertAlmostEqual(
            abs(liquidity_line.balance),
            forced_amount,
            places=2,
            msg="Liquidity line balance should equal the forced company currency amount, "
            "not the payment total. This was the main bug: the withholding adjustment "
            "was overwriting the forced amount.",
        )

        # The liquidity line balance must NOT equal payment_total (which includes withholdings)
        self.assertNotAlmostEqual(
            abs(liquidity_line.balance),
            payment.payment_total,
            places=2,
            msg="Liquidity line balance should NOT equal payment_total when force amount is set",
        )

        # The counterpart (payable) line must equal liquidity + withholdings (journal entry balances to 0)
        expected_counterpart = forced_amount + withholding_amount
        self.assertAlmostEqual(
            abs(counterpart_line.balance),
            expected_counterpart,
            places=2,
            msg="Counterpart line balance should equal liquidity + withholdings "
            "(the journal entry must balance to zero).",
        )

        # Withholding lines should have the correct amount
        total_withholding_balance = abs(sum(withholding_tax_lines.mapped("balance")))
        self.assertAlmostEqual(
            total_withholding_balance,
            withholding_amount,
            places=2,
            msg="Withholding lines balance should match the computed withholdings amount",
        )

    def test_force_amount_company_currency_withholdings_no_autobalance(self):
        """Regression for ticket 119846.

        A supplier payment in COMPANY currency (ARS) with withholdings and
        force_amount_company_currency set (the flow used by the "Multiple payments" payment
        group / account_payment_pro) must NOT produce an "Automatic Balancing Line".

        Bug scenario: _prepare_move_lines_per_type skipped the *balance* adjustment when the
        amount was forced, but still re-adjusted *amount_currency* of the liquidity and
        counterpart lines. In company currency amount_currency must equal balance, so the
        re-adjustment desynced both, leaving the journal entry unbalanced. Odoo then inserted an
        automatic balancing line into the journal's default account instead of keeping the real
        liquidity line (exactly what happened on payment OP-X 0001-00003040 / move 30114).

        Expected behavior:
        - No automatic balancing line in the move.
        - The journal entry balances to zero.
        - Being in company currency, every line keeps amount_currency == balance.
        - A real liquidity line exists (it was not dropped/replaced by the plug).
        """
        # 1. Vendor bill in ARS (company currency) for a CABA partner
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
                "l10n_latam_document_number": "1-119846",
            }
        )
        invoice.action_post()

        # 2. Fiscal position with IIBB CABA withholding for this partner
        fiscal_pos = self.env["account.fiscal.position"].create(
            {
                "name": "IIBB CABA 119846",
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

        # 3. Register a payment for the bill (ARS bank journal)
        action_context = invoice.action_register_payment()["context"]
        payment = (
            self.env["account.payment"]
            .with_context(**action_context)
            .create(
                {
                    "journal_id": self.company_bank_journal.id,
                    "amount": invoice.amount_total,
                    "date": self.today,
                }
            )
        )
        self.assertTrue(payment.l10n_ar_withholding_line_ids, "Withholdings should have been computed")
        self.assertGreater(payment.withholdings_amount, 0, "Withholding amount should be positive")
        self.assertEqual(
            payment.currency_id,
            payment.company_id.currency_id,
            "This regression test must run on a company-currency (ARS) payment",
        )

        # 4. Force the company-currency amount (what the multiple-payments / group flow does)
        payment.force_amount_company_currency = payment.amount_company_currency
        self.assertTrue(payment.force_amount_company_currency)

        # 5. Post the payment to materialize the journal entry
        payment.action_post()
        self.assertTrue(payment.move_id, "Payment should have a journal entry after posting")

        # 6a. No automatic balancing line should have been inserted
        auto_balance_lines = payment.move_id.line_ids.filtered(
            lambda l: "automatic balancing" in (l.name or "").lower() or "balance automático" in (l.name or "").lower()
        )
        self.assertFalse(
            auto_balance_lines,
            "No automatic balancing line should be needed: when the amount is forced in company "
            "currency, amount_currency must stay equal to balance so the entry already balances.",
        )

        # 6b. The journal entry must balance to zero
        self.assertTrue(
            payment.company_currency_id.is_zero(sum(payment.move_id.line_ids.mapped("balance"))),
            "The journal entry must balance to zero.",
        )

        # 6c. Being in company currency, every line must keep amount_currency == balance
        for line in payment.move_id.line_ids:
            self.assertAlmostEqual(
                line.amount_currency,
                line.balance,
                places=2,
                msg="In a company-currency payment every move line must keep amount_currency == balance "
                "(account %s)." % line.account_id.code,
            )

        # 6d. A real liquidity line to the outstanding account must exist (not dropped/replaced by the plug)
        liquidity_line = payment.move_id.line_ids.filtered(lambda l: l.account_id == payment.outstanding_account_id)
        self.assertTrue(
            liquidity_line,
            "The real liquidity line must be present (it was being removed and replaced by an "
            "automatic balancing line in the journal default account).",
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

        # Verify there is no force_amount_company_currency
        self.assertFalse(payment.force_amount_company_currency)

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
