# © ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.addons.l10n_ar_tax.tests.common import WithholdingCommon
from odoo.addons.l10n_latam_check.models.account_payment import AccountPayment as LatamCheckPayment
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestWithholdingGrossAmount(WithholdingCommon):
    """In 20 the payment amount is the gross one (paid + withheld). With payment pro the user keeps working
    with the net amount, the withholding mode follows the withholding lines, and the gross amount follows the
    selected debt only where it did in 19.0.
    """

    def test_the_user_types_the_net_amount_and_the_payment_keeps_the_gross_one(self):
        payment = self._payment()
        self.assertEqual(payment.withholding_amount, 20.0)

        payment.withholding_net_amount = 980.0

        self.assertEqual(payment.amount, 1000.0, "gross = net + withholdings")
        self.assertEqual(payment.amount_exact, 1000.0)
        self.assertEqual(payment.payment_total, 1000.0, "the payment total already includes the withholdings")

    def test_list_amounts_show_the_net_amount(self):
        payment = self._payment()
        self.assertEqual(payment.withholding_net_amount_signed, -980.0)
        self.assertEqual(payment.amount_company_currency_signed, -980.0, "a draft shows what goes through the bank")
        payment.action_post()
        self.assertEqual(payment.amount_company_currency_signed, -980.0)

    def test_the_debt_currency_amount_is_also_net(self):
        foreign = self.setup_other_currency("EUR", rates=[("2000-01-01", 1.0)])
        payment = self._payment()
        payment.counterpart_currency_id = foreign
        payment.counterpart_rate = 0.5
        payment.counterpart_currency_amount = 500.0
        self.assertEqual(payment.counterpart_currency_net_amount, 490.0, "500 gross - 20 withheld * 0.5")

        payment.counterpart_currency_net_amount = 480.0

        self.assertEqual(payment.counterpart_currency_amount, 490.0)
        self.assertEqual(payment.amount, 980.0)

    def test_the_withholdings_total_is_shown_in_the_debt_currency(self):
        """The lines stay in the payment currency; the total next to the payment total is in the debt one."""
        foreign = self.setup_other_currency("EUR", rates=[("2000-01-01", 1.0)])
        payment = self._payment()
        payment.counterpart_currency_id = foreign
        payment.counterpart_rate = 0.5
        self.assertEqual(payment.withholding_amount, 20.0)
        self.assertEqual(payment.destination_currency_withholding_amount, 10.0, "20 withheld * 0.5")
        self.assertEqual(
            payment.counterpart_currency_net_amount + payment.destination_currency_withholding_amount,
            payment.payment_total,
        )

    def test_the_withholdings_total_reconciling_on_company_currency(self):
        """Reconciling on company currency the debt currency is the company one, at the accounting rate."""
        foreign = self.setup_other_currency("EUR", rates=[("2000-01-01", 1.0)])
        # the flag is only allowed in Argentina
        self.company.country_id = self.env.ref("base.ar")
        self.company.reconcile_on_company_currency = True
        # a receipt with a suffered withholding, typed as the certificate says
        receipt = self._payment(
            withholding_base=0.0, partner_type="customer", payment_type="inbound", currency_id=foreign.id
        )
        # 1 company unit = 0.5 EUR
        receipt.accounting_rate = 0.5
        receipt.withholding_line_ids = [
            Command.create({"tax_id": self.sale_withholding_tax.id, "base_amount": 1000.0, "amount": 20.0})
        ]

        self.assertEqual(receipt.withholding_amount, 20.0)
        self.assertEqual(receipt.destination_currency_id, self.company.currency_id)
        self.assertEqual(receipt.destination_currency_withholding_amount, 40.0, "20 EUR / 0.5")
        self.assertEqual(receipt.payment_total, 2000.0)

    def test_the_mode_follows_the_withholding_lines(self):
        payment = self._payment(withholding_base=0.0)
        self.assertEqual(payment.withhold, "payment")

        payment.withholding_line_ids = [Command.create({"tax_id": self.withholding_tax.id, "base_amount": 1000.0})]
        self.assertEqual(payment.withhold, "withhold_pay")

        payment.withholding_net_amount = 0.0
        self.assertEqual(payment.amount, 20.0)
        self.assertEqual(payment.withhold, "withhold", "nothing goes through the bank")

    def test_the_entry_pays_the_net_and_cancels_the_gross(self):
        payment = self._payment()
        payment.action_post()

        liquidity, counterpart, _writeoff = payment._seek_for_lines()
        tax_line = payment.move_id.line_ids.filtered(lambda line: line.tax_line_id == self.withholding_tax)
        self.assertEqual(sum(liquidity.mapped("balance")), -980.0)
        self.assertEqual(sum(counterpart.mapped("balance")), 1000.0)
        self.assertEqual(tax_line.balance, -20.0)

    def test_a_withholding_only_payment_has_no_bank_line(self):
        payment = self._payment(amount=20.0)
        self.assertEqual(payment.withhold, "withhold")
        payment.action_post()

        liquidity, counterpart, _writeoff = payment._seek_for_lines()
        self.assertFalse(liquidity)
        self.assertEqual(sum(counterpart.mapped("balance")), 20.0)

    def test_a_foreign_currency_withholding_uses_the_rate_of_the_payment(self):
        foreign = self.setup_other_currency("EUR", rates=[("2000-01-01", 1.0)])
        payment = self._payment(currency_id=foreign.id)
        # 1 company unit = 0.5 EUR -> 1 EUR = 2 company units, not the 1:1 of the day
        payment.accounting_rate = 0.5
        payment.action_post()

        liquidity, counterpart, _writeoff = payment._seek_for_lines()
        tax_line = payment.move_id.line_ids.filtered(lambda line: line.tax_line_id == self.withholding_tax)
        self.assertEqual(tax_line.amount_currency, -20.0)
        self.assertEqual(tax_line.balance, -40.0)
        self.assertEqual(sum(liquidity.mapped("balance")), -1960.0)
        self.assertEqual(sum(counterpart.mapped("balance")), 2000.0)

    def test_the_entry_books_the_company_currency_amounts_of_the_line(self):
        """A localization that computes the withholding in company currency gives the exact amounts: the entry books
        them instead of converting back the rounded line, and the bank line absorbs the difference."""
        foreign = self.setup_other_currency("EUR", rates=[("2000-01-01", 1.0)])
        payment = self._payment(currency_id=foreign.id)
        payment.accounting_rate = 0.5
        exact = {"base_amount": 2000.0, "amount": 39.99}
        line_model = type(payment.withholding_line_ids)
        with patch.object(line_model, "_get_company_currency_amounts", lambda line: exact):
            payment.action_post()

        liquidity, counterpart, _writeoff = payment._seek_for_lines()
        tax_line = payment.move_id.line_ids.filtered(lambda line: line.tax_line_id == self.withholding_tax)
        self.assertEqual(tax_line.amount_currency, -20.0)
        self.assertEqual(tax_line.balance, -39.99)
        self.assertEqual(tax_line.tax_base_amount, -2000.0)
        self.assertEqual(sum(liquidity.mapped("balance")), -1960.01)
        self.assertEqual(sum(counterpart.mapped("balance")), 2000.0)

    def test_the_withholdings_total_in_company_currency_matches_the_entry(self):
        """Paying a debt in company currency from a foreign journal, the withholdings of the header are the ones the
        entry books: they are not rounded back through the payment currency."""
        foreign = self.setup_other_currency("EUR", rates=[("2000-01-01", 1.0)])
        payment = self._payment(currency_id=foreign.id)
        payment.accounting_rate = 0.5
        self.assertEqual(payment.counterpart_currency_id, self.company.currency_id)
        exact = {"base_amount": 2000.0, "amount": 39.99}
        line_model = type(payment.withholding_line_ids)
        with patch.object(line_model, "_get_company_currency_amounts", lambda line: exact):
            payment.invalidate_recordset(["destination_currency_withholding_amount", "counterpart_currency_net_amount"])
            self.assertEqual(
                payment.destination_currency_withholding_amount, 39.99, "and not the 40.0 of 20 EUR at 0.5"
            )
            payment.action_post()

            liquidity, _counterpart, _writeoff = payment._seek_for_lines()
            self.assertEqual(
                payment.counterpart_currency_net_amount,
                -sum(liquidity.mapped("balance")),
                "what the header shows paid is what the bank line of the entry shows",
            )

    # the gross amount follows the selected debt: supplier payments only, as in 19.0

    def test_the_amount_follows_the_debt_when_the_withholdings_change(self):
        """Removing a bill changes the base of the withholdings, and then the gross amount follows the remaining
        debt, as the net one did in 19."""
        bills = self.init_invoice("in_invoice", partner=self.partner_a, amounts=[1000.0], post=True)
        bills |= self.init_invoice("in_invoice", partner=self.partner_a, amounts=[500.0], post=True)
        debt = bills.line_ids.filtered(lambda line: line.account_id.account_type == "liability_payable")
        payment = self._payment(withholding_base=1500.0, amount=1500.0, to_pay_move_line_ids=[Command.set(debt.ids)])

        payment.to_pay_move_line_ids = [Command.unlink(debt.filtered(lambda line: line.move_id == bills[0]).id)]
        payment.withholding_line_ids.base_amount = 500.0
        payment._onchange_withholding_amount()

        self.assertEqual(payment.amount, 500.0, "the gross amount is the remaining debt")
        self.assertEqual(payment.withholding_net_amount, 490.0)

    def test_changing_the_partner_moves_the_amount_to_its_debt(self):
        self._bill(self.partner_a, 400.0)
        bill_b = self._bill(self.partner_b, 100.0)
        form = self._supplier_payment_form()
        form.partner_id = self.partner_a
        self.assertEqual(form.amount, 400.0)

        form.partner_id = self.partner_b

        self.assertEqual(form.amount, bill_b.amount_total, "the amount goes down to the debt of the new partner")

    def test_changing_the_withholdings_moves_the_amount_to_the_debt(self):
        bill_1 = self._bill(self.partner_a, 100.0)
        self._bill(self.partner_a, 300.0)
        form = self._supplier_payment_form(self.partner_a)
        self.assertEqual(form.amount, 400.0)
        payment = form.save()
        payment.withholding_line_ids = [Command.create({"tax_id": self.withholding_tax.id, "base_amount": 400.0})]
        other_line = payment.to_pay_move_line_ids.filtered(lambda line: line.move_id != bill_1)

        with Form(payment) as form:
            form.to_pay_move_line_ids.remove(id=other_line.id)
            with form.withholding_line_ids.edit(0) as line:
                line.base_amount = 100.0

        self.assertEqual(payment.amount, 100.0, "the gross amount is the selected debt")
        self.assertEqual(payment.withholding_net_amount, 98.0)

    def test_without_a_change_of_withholdings_the_amount_is_kept(self):
        bill_1 = self._bill(self.partner_a, 100.0)
        self._bill(self.partner_a, 300.0)
        payment = self._payment(withholding_base=0.0, amount=400.0)
        other_line = payment.to_pay_move_line_ids.filtered(lambda line: line.move_id != bill_1)

        with Form(payment) as form:
            form.to_pay_move_line_ids.remove(id=other_line.id)

        self.assertEqual(payment.selected_debt, 100.0)
        self.assertEqual(payment.amount, 400.0, "as in 19.0, removing a bill alone does not touch the amount")

    # in a receipt the net the user typed stays put: the gross grows and the gap goes to the adjustment

    def test_the_withholding_does_not_move_the_amount_of_a_receipt(self):
        self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000.0], taxes=[], post=True)
        form = self._receipt_form(self.partner_a)
        self.assertEqual(form.amount, 1000.0)

        self._add_withholding(form, 1000.0, self.sale_withholding_tax)

        self.assertEqual(form.withholding_net_amount, 1000.0, "the net the user sees stays where it was")
        self.assertEqual(form.amount, 1020.0, "the gross grows by the withholding")
        self.assertEqual(form.payment_total, 1020.0)
        self.assertEqual(form.payment_difference, -20.0, "the difference is left for the user to adjust")

    def test_editing_the_withholding_moves_the_gross_by_the_delta(self):
        self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000.0], taxes=[], post=True)
        form = self._receipt_form(self.partner_a)
        self._add_withholding(form, 1000.0, self.sale_withholding_tax)

        with form.withholding_line_ids.edit(0) as line:
            line.base_amount = 500.0

        self.assertEqual(form.withholding_net_amount, 1000.0, "the net is still the one the user typed")
        self.assertEqual(form.amount, 1010.0, "only the delta of the withholding moved the gross")

    def test_the_supplier_payment_still_follows_the_debt(self):
        self.init_invoice("in_invoice", partner=self.partner_a, amounts=[1000.0], taxes=[], post=True)
        form = self._supplier_payment_form(self.partner_a)

        self._add_withholding(form, 1000.0)

        self.assertEqual(form.amount, 1000.0, "the gross stays on the debt")
        self.assertEqual(form.withholding_net_amount, 980.0, "the net is what goes through the bank")
        self.assertEqual(form.payment_difference, 0.0)

    def _bill(self, partner, amount):
        return self.init_invoice("in_invoice", partner=partner, amounts=[amount], taxes=[], post=True)


@tagged("post_install", "-at_install")
class TestWithholdingGrossAmountChecks(TestArCommon):
    """With checks the checks are the net amount: the gross one adds the withholdings.

    Its own class because the checks need the Argentinian chart of accounts, not the generic company.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_ri
        cls.company.use_payment_pro = True
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))
        if not cls.company.withholding_tax_base_account_id:
            cls.company.withholding_tax_base_account_id = cls.env["account.account"].create(
                {"code": "WITHB", "name": "Withholding Tax Base", "account_type": "asset_current"}
            )
        cls.withholding_tax = cls.env["account.tax"].create(
            {
                "name": "Suffered withholding 2%",
                "amount_type": "percent",
                "amount": -2.0,
                "type_tax_use": "sale",
                "is_withholding_tax": True,
                "company_id": cls.company.id,
            }
        )
        cls.method_line = cls.env["account.payment.method.line"].search(
            [
                ("journal_id.company_id", "=", cls.company.id),
                ("payment_type", "=", "inbound"),
                ("code", "=", "new_third_party_checks"),
            ],
            limit=1,
        )

    def _receipt_with_check(self, check_amount=980.0, withholding_base=1000.0, check_number="00000001"):
        """A draft receipt collected with a third party check, with one suffered withholding over its base."""
        receipt = Form(
            self.env["account.payment"].with_context(default_payment_type="inbound", default_partner_type="customer")
        )
        receipt.partner_id = self.res_partner_adhoc
        receipt.journal_id = self.method_line.journal_id
        receipt.payment_method_line_id = self.method_line
        with receipt.l10n_latam_new_check_ids.new() as check:
            check.name = check_number
            check.payment_date = fields.Date.today()
            check.amount = check_amount
        payment = receipt.save()
        payment.withholding_line_ids = [
            Command.create({"tax_id": self.withholding_tax.id, "base_amount": withholding_base})
        ]
        return payment

    def test_the_checks_are_the_net_amount(self):
        payment = self._receipt_with_check()

        self.assertEqual(payment.amount, 1000.0, "gross = checks + withholdings")
        self.assertEqual(payment.withholding_net_amount, 980.0)
        self.assertEqual(payment.withhold, "withhold_pay")
        self.assertFalse(payment._get_blocking_l10n_latam_warning_msg(), "the checks match the net amount")

        payment.action_amount_from_checks()
        self.assertEqual(payment.amount, 1000.0)

    def test_the_core_check_warning_is_dropped_whatever_the_language(self):
        """The core message is found by its source string, not by its translation.

        Each module translates the same msgid with its own catalog: the core says "monto" and payment pro
        "importe", so comparing the translated texts only matched in English and the warning blocked the
        confirmation of every check payment with withholdings in Spanish.

        Shown in red by comparing the translated texts again: the warning comes back.
        """
        payment = self._receipt_with_check()
        core_translation = "El monto del pago no coincide con el monto del cheque seleccionado."

        def core_msgs(records):
            # what the core does with the user in Spanish: its own catalog, which payment pro does not share
            if records.env.context.get("lang") == "en_US":
                return [records.MISMATCH_CHECK_AMOUNT_MSG]
            return [core_translation]

        with patch.object(LatamCheckPayment, "_get_blocking_l10n_latam_warning_msg", core_msgs):
            msgs = payment._get_blocking_l10n_latam_warning_msg()

        self.assertFalse(msgs, "the checks match the net amount, so nothing blocks the payment")

    def test_posting_does_not_move_the_gross_amount(self):
        """A withholding written once the payment left the draft state does not move its amount.

        l10n_ar_tax numbers the withholdings inside ``action_post``, writing the one2many, and that recomputes
        the amount: the gross one of a posted payment is the one it was confirmed with.

        Shown in red by dropping the draft guard of ``_compute_amount``: the amount follows the new withholding
        and the posted payment ends up with another one.
        """
        payment = self._receipt_with_check()
        # the number l10n_ar_tax would give it on post, so the sequence of its tax group is not needed here
        payment.withholding_line_ids.name = "0001-00000001"
        payment.action_post()
        self.assertNotEqual(payment.state, "draft")
        amount = payment.amount

        # the shape of the write l10n_ar_tax does when it numbers the withholdings of the payment
        payment.withholding_line_ids = [Command.update(payment.withholding_line_ids.id, {"amount": 25.0})]

        self.assertEqual(payment.amount, amount, "the gross amount is the one the payment was posted with")
        self.assertEqual(payment.withholding_net_amount, amount - 25.0, "the net one follows from it")
