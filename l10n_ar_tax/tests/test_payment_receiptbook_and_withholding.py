from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi


class TestPaymentReceiptbookAndWithholding(TestArWithholdingArRi):
    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.company_bank_journal = self.env["account.journal"].search(
            [("company_id", "=", self.company_ri.id), ("type", "=", "bank")], limit=1
        )

    # ------------------------------------------------------------------
    # Helpers for withholding + write off scenarios (ticket 123082)
    # ------------------------------------------------------------------
    def _write_off_type(self):
        """A write off type pointing to an expense account of company_ri."""
        account = self.env["account.account"].search(
            [("company_ids", "=", self.company_ri.id), ("account_type", "=", "expense")],
            limit=1,
        )
        return self.env["account.write_off.type"].create(
            {
                "name": "Write Off Test 123082",
                "account_id": account.id,
            }
        )

    def _caba_withholding_fiscal_position(self, name):
        """CABA IIBB withholding auto-applied fiscal position for the RI company."""
        fiscal_pos = self.env["account.fiscal.position"].create(
            {
                "name": name,
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
        return fiscal_pos

    def _assert_signs_consistent(self, payment):
        """Every payable/liquidity move line must have amount_currency and balance with the
        same sign. This is exactly what the ticket 123082 fix guarantees for the counterpart
        line when combining withholdings with a write off (the bug produced a counterpart line
        whose amount_currency sign did not match its balance)."""
        for line in payment.move_id.line_ids:
            if line.company_currency_id.is_zero(line.balance) or not line.amount_currency:
                continue
            self.assertEqual(
                line.balance > 0,
                line.amount_currency > 0,
                "Move line '%s' has balance %s but amount_currency %s (sign mismatch)"
                % (line.name, line.balance, line.amount_currency),
            )

    def _assert_balanced(self, payment):
        self.assertEqual(payment.move_id.state, "posted")
        self.assertTrue(
            payment.company_currency_id.is_zero(sum(payment.move_id.line_ids.mapped("balance"))),
            "The journal entry must balance to zero",
        )

    def test_withholding_and_negative_write_off_company_currency(self):
        """Ticket 123082: supplier payment with a withholding AND a negative write off, in the
        company currency (ARS).

        Combining withholdings with a write off recomputes the counterpart line balance in
        l10n_ar_tax. Regression guard: the journal entry must stay balanced and the counterpart
        line's amount_currency sign must match its balance sign.
        """
        write_off_type = self._write_off_type()
        self._caba_withholding_fiscal_position("IIBB CABA 123082 ARS")

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
                "l10n_latam_document_number": "1-1230821",
            }
        )
        invoice.action_post()

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
        withholding_amount = payment.withholdings_amount
        self.assertGreater(withholding_amount, 0)

        # Negative write off (e.g. a rounding/discount adjustment against the debt).
        payment.write_off_type_id = write_off_type
        payment.write_off_amount = -1500.0

        payment.action_post()

        self._assert_balanced(payment)
        self._assert_signs_consistent(payment)

        # Withholding line materialised with the computed amount.
        withholding_tax_lines = payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id)
        self.assertAlmostEqual(
            abs(sum(withholding_tax_lines.mapped("balance"))),
            withholding_amount,
            places=2,
            msg="Withholding lines must carry the computed amount",
        )
        # Write off line materialised on the journal entry.
        write_off_line = payment.move_id.line_ids.filtered(lambda l: l.account_id == write_off_type.account_id)
        self.assertTrue(write_off_line, "The write off line must exist on the journal entry")

    def test_withholding_and_negative_write_off_counterpart_currency(self):
        """Ticket 123082 (the specific fix): supplier payment in the company currency (ARS) that
        pays a foreign-currency (USD) bill keeping the debt tracked in USD via the counterpart
        currency, combined with a withholding AND a negative write off.

        This exercises the ``_use_counterpart_currency()`` branch of
        ``_prepare_move_lines_per_type``. The counterpart line's amount_currency (USD) is set from
        the sign of the balance BEFORE the withholding adjustment (``balance -= wth_balance``).
        When the negative write off leaves that pre-adjustment balance in the ``(-wth_balance, 0)``
        window, the withholding adjustment flips the balance sign, so without the fix the
        amount_currency keeps the opposite sign and posting fails with the database check
        constraint ``account_move_line_check_amount_currency_balance_sign``. The fix re-syncs the
        amount_currency sign to the final balance.

        The write off amount (-252000) is chosen so the counterpart balance lands in that window
        (net payment ~ +10000 ARS against a ~ -20000 ARS withholding adjustment).
        """
        usd = self.other_currency
        write_off_type = self._write_off_type()
        self._caba_withholding_fiscal_position("IIBB CABA 123082 Counterpart")

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
                "l10n_latam_document_number": "1-1230823",
            }
        )
        invoice.action_post()

        # Pay in company currency (ARS) but keep the counterpart tracked in the bill currency (USD).
        action_context = invoice.action_register_payment()["context"]
        payment = (
            self.env["account.payment"]
            .with_context(**action_context)
            .create(
                {
                    "journal_id": self.company_bank_journal.id,
                    "currency_id": self.company_ri.currency_id.id,
                    "date": self.today,
                }
            )
        )
        payment.counterpart_currency_id = usd
        self.assertTrue(payment._use_counterpart_currency(), "Test must exercise the counterpart currency branch")
        self.assertTrue(payment.l10n_ar_withholding_line_ids, "Withholdings should have been computed")
        withholding_amount = payment.withholdings_amount
        self.assertGreater(withholding_amount, 0)

        payment.write_off_type_id = write_off_type
        payment.write_off_amount = -252000.0

        # Without the fix this raises the amount_currency/balance sign check constraint.
        payment.action_post()

        self._assert_balanced(payment)
        self._assert_signs_consistent(payment)

        # The counterpart (payable) line must be expressed in the counterpart currency (USD) and
        # its amount_currency sign must match its balance sign.
        counterpart_line = payment.move_id.line_ids.filtered(lambda l: l.account_type == "liability_payable")
        self.assertTrue(counterpart_line, "There must be a counterpart payable line")
        self.assertEqual(
            counterpart_line.currency_id,
            usd,
            "The counterpart line must be tracked in the counterpart currency (USD)",
        )
        self.assertEqual(
            counterpart_line.balance > 0,
            counterpart_line.amount_currency > 0,
            "Counterpart line balance and amount_currency must share sign (ticket 123082 fix)",
        )
        write_off_line = payment.move_id.line_ids.filtered(lambda l: l.account_id == write_off_type.account_id)
        self.assertTrue(write_off_line, "The write off line must exist on the journal entry")

    def test_withholding_and_negative_write_off_foreign_currency(self):
        """Ticket 123082: supplier payment with a withholding AND a negative write off, in a
        foreign currency (USD).

        Same as the company-currency case but the payment (and bill) are in USD, so the amount
        currency values differ from the company-currency balances. The entry must stay balanced
        and every line's amount_currency sign must match its balance sign.
        """
        usd = self.other_currency
        write_off_type = self._write_off_type()
        usd_bank_journal = self.env["account.journal"].create(
            {
                "name": "Bank USD 123082",
                "type": "bank",
                "code": "BU308",
                "company_id": self.company_ri.id,
                "currency_id": usd.id,
            }
        )
        self._caba_withholding_fiscal_position("IIBB CABA 123082 USD")

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
                "l10n_latam_document_number": "1-1230822",
            }
        )
        invoice.action_post()

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

        payment.write_off_type_id = write_off_type
        payment.write_off_amount = -1500.0  # write_off_amount is in company currency (ARS)

        payment.action_post()

        self._assert_balanced(payment)
        self._assert_signs_consistent(payment)

        withholding_tax_lines = payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id)
        self.assertAlmostEqual(
            abs(sum(withholding_tax_lines.mapped("balance"))),
            withholding_amount,
            places=2,
            msg="Withholding lines must carry the computed ARS amount",
        )
        write_off_line = payment.move_id.line_ids.filtered(lambda l: l.account_id == write_off_type.account_id)
        self.assertTrue(write_off_line, "The write off line must exist on the journal entry")

    def test_reset_to_draft_keeps_manual_withholding_line(self):
        """Regression for ticket 119846 (reset to draft drops a manual-amount withholding line).

        Faithful reproduction of the sinax case: a supplier payment with a withholding whose tax
        is ``fixed`` with ``amount = 0`` (e.g. "Retención IVA"), where the withheld amount is
        entered manually by the operator. ``account.tax.compute_all`` returns 0 for such a tax,
        so when the payment is reset to draft the standard dynamic tax sync recomputes the
        withholding tax line to 0, drops it via the zero-amount filter, leaves the entry
        unbalanced and inserts an "Automatic Balancing Line".

        Posting works (both dynamic-sync managers skip posted moves); only reset to draft was
        affected. The fix forces ``round_from_tax_lines=True`` for payment moves with
        withholdings so the manually entered amount on the existing tax line is preserved instead
        of recomputed from the base.
        """
        manual_wth_amount = 50000.0
        manual_tax = self.tax_wth_test_1

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
                "l10n_latam_document_number": "1-1198461",
            }
        )
        invoice.action_post()

        # 2. Fiscal position with the manual (fixed/0) withholding for this partner
        fiscal_pos = self.env["account.fiscal.position"].create(
            {
                "name": "Ret IVA manual 119846",
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
                "default_tax_id": manual_tax.id,
                "tax_type": "withholding",
            }
        )

        # 3. Register the payment and enter the withholding amount manually
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
        wth_line = payment.l10n_ar_withholding_line_ids.filtered(lambda l: l.tax_id == manual_tax)
        self.assertTrue(wth_line, "The withholding line should have been created")

        # Turn the resolved withholding into a manual one (fixed/0, like the real "Retención IVA"
        # tax 301): the standard engine now computes 0 for it, and the operator enters the amount.
        manual_tax.write({"amount_type": "fixed", "amount": 0.0})
        wth_line.amount = manual_wth_amount

        # 4. Post and confirm the manual amount materialised on the journal entry
        payment.action_post()
        self.assertEqual(payment.move_id.state, "posted")
        posted_wth_lines = payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id)
        self.assertTrue(posted_wth_lines, "Posted move must have a withholding tax line")
        self.assertAlmostEqual(
            abs(sum(posted_wth_lines.mapped("balance"))),
            manual_wth_amount,
            places=2,
            msg="The manually entered withholding amount must be on the posted journal entry",
        )
        posted_wth_count = len(posted_wth_lines)
        posted_wth_balance = sum(posted_wth_lines.mapped("balance"))
        self.assertTrue(
            payment.company_currency_id.is_zero(sum(payment.move_id.line_ids.mapped("balance"))),
            "Posted journal entry must balance to zero",
        )

        # 5. Reset the payment to draft
        payment.action_draft()
        self.assertEqual(payment.move_id.state, "draft")

        # 6a. No automatic balancing line should have been inserted
        auto_balance_lines = payment.move_id.line_ids.filtered(
            lambda l: "automatic balancing" in (l.name or "").lower() or "balance automático" in (l.name or "").lower()
        )
        self.assertFalse(
            auto_balance_lines,
            "Resetting to draft must NOT insert an automatic balancing line: the manual "
            "withholding line must be preserved, not recomputed to 0 and dropped.",
        )

        # 6b. The journal entry must still balance to zero
        self.assertTrue(
            payment.company_currency_id.is_zero(sum(payment.move_id.line_ids.mapped("balance"))),
            "Journal entry must still balance to zero after reset to draft",
        )

        # 6c. The manual withholding line must survive with its amount intact
        draft_wth_lines = payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id)
        self.assertEqual(
            len(draft_wth_lines),
            posted_wth_count,
            "The manual withholding line must survive the reset to draft (none dropped).",
        )
        self.assertAlmostEqual(
            sum(draft_wth_lines.mapped("balance")),
            posted_wth_balance,
            places=2,
            msg="The withholding line must keep its manual amount after reset to draft.",
        )

    def test_reset_to_draft_change_withholding_amount_and_repost(self):
        """Regression for ticket #118586 (PR #1464): a payment with automatic withholdings must
        allow reset to draft, editing the withholding amount, and re-confirming.

        Reproduces feg's video step-by-step: register a supplier payment that auto-computes a
        withholding, override its amount with our own value, post it, then reset to draft, change
        the withholding amount, and post again.

        The bug: withholding move lines carried ``tax_repartition_line_id`` and were classified as
        ``display_type='tax'``, so on the next ``_synchronize_to_moves`` rebuild (triggered by
        reset to draft) ``_prevent_automatic_line_deletion`` raised a ``ValidationError`` and the
        cycle blew up. We assert the functional outcome instead of internal flags: the whole
        post → draft → edit amount → post cycle succeeds and the journal entry reflects the edited
        amount while staying balanced.
        """
        first_amount = 30000.0
        second_amount = 45000.0

        # 1. Vendor bill for a CABA partner and post.
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
                "l10n_latam_document_number": "1-1464",
            }
        )
        invoice.action_post()

        # 2. Fiscal position with the CABA withholding for this partner (auto-applied).
        fiscal_pos = self.env["account.fiscal.position"].create(
            {
                "name": "IIBB CABA 1464",
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

        # 3. Register the payment: the withholding is computed automatically from the tax.
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
        wth_line = payment.l10n_ar_withholding_line_ids.filtered(lambda l: l.tax_id == self.tax_wth_test_1)
        self.assertTrue(wth_line, "The automatic withholding line should have been created")

        def posted_withholding_balance():
            move_lines = payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id)
            return abs(sum(move_lines.mapped("balance")))

        def assert_balanced():
            self.assertTrue(
                payment.company_currency_id.is_zero(sum(payment.move_id.line_ids.mapped("balance"))),
                "The journal entry must balance to zero",
            )

        # 4. Override the withholding amount with our own value and post. We write through the
        # parent One2many (like the form does) so the change marks the payment dirty and
        # _synchronize_to_moves rebuilds the journal entry from the edited amount.
        payment.l10n_ar_withholding_line_ids = [Command.update(wth_line.id, {"amount": first_amount})]
        payment.action_post()
        self.assertEqual(payment.move_id.state, "posted")
        assert_balanced()
        self.assertAlmostEqual(
            posted_withholding_balance(),
            first_amount,
            places=2,
            msg="The posted withholding line must reflect the amount we entered",
        )

        # 5. Reset to draft: this rebuilds the payment lines via _synchronize_to_moves. Before the
        # fix it raised a ValidationError trying to delete the 'tax' withholding lines.
        payment.action_draft()
        self.assertEqual(payment.move_id.state, "draft")

        # 6. Change the withholding amount and confirm again.
        payment.l10n_ar_withholding_line_ids = [Command.update(wth_line.id, {"amount": second_amount})]
        payment.action_post()
        self.assertEqual(payment.move_id.state, "posted")
        assert_balanced()
        self.assertAlmostEqual(
            posted_withholding_balance(),
            second_amount,
            places=2,
            msg="After reset to draft and editing, the journal entry must reflect the new " "withholding amount",
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
