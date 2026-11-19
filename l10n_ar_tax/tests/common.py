from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import Form


class L10nArTaxPaymentCommon(TestArCommon):
    """Supplier payment pro payments that propose their withholdings from a fiscal position, as the user registers
    them from the bill (company RI, 2023-01-01, ARS)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.use_payment_pro = True
        cls.env.company.withholding_tax_base_account_id = cls.env.ref(
            "account.%i_base_tax_account" % cls.env.company.id
        )
        cls.tax_21 = cls.env.ref("account.%s_ri_tax_vat_21_ventas" % cls.env.company.id)
        cls.tax_21_purchase = cls.env.ref("account.%s_ri_tax_vat_21_compras" % cls.env.company.id)
        cls.withholding_account = cls.env["account.account"].create(
            {"name": "Withholdings to pay", "code": "WTH.001", "account_type": "liability_current"}
        )
        cls.withholding_sequence = cls.env["ir.sequence"].create(
            {"implementation": "standard", "name": "tax wth test", "padding": 8, "number_increment": 1}
        )
        cls.bank_journal = cls.company_data["default_journal_bank"]

        cls.tax_earnings_scale = cls._create_withholding_tax(
            "Test Profits WTH regimen 110",
            -1,
            l10n_ar_withholding_tax_type="earnings_scale",
            l10n_ar_scale_id=cls.env.ref("l10n_ar_withholding.normal_scale").id,
            l10n_ar_code="110",
            l10n_ar_non_taxable_amount=10000.0,
        )
        cls.tax_earnings = cls._create_withholding_tax(
            "Test Profits WTH regimen 35",
            -6,
            l10n_ar_withholding_tax_type="earnings",
            l10n_ar_code="35",
            l10n_ar_non_taxable_amount=7870.0,
        )
        cls.tax_iibb_untaxed = cls._create_withholding_tax(
            "Test IIBB WTH 3%",
            -3,
            l10n_ar_withholding_tax_type="iibb_untaxed",
            l10n_ar_state_id=cls.env.ref("base.state_ar_c").id,
        )

    @classmethod
    def _create_withholding_tax(cls, name, amount, **tax_vals):
        return cls.env["account.tax"].create(
            {
                "name": name,
                "amount_type": "percent",
                "amount": amount,
                "type_tax_use": "purchase",
                "is_withholding_tax": True,
                "withholding_sequence_id": cls.withholding_sequence.id,
                "company_id": cls.env.company.id,
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": cls.withholding_account.id}),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": cls.withholding_account.id}),
                ],
                **tax_vals,
            }
        )

    def _fiscal_position(self, taxes):
        """A fiscal position that withholds the given taxes, one line each."""
        fiscal_position = self.env["account.fiscal.position"].create(
            {"name": "Withholding %s" % ", ".join(taxes.mapped("name")), "company_id": self.env.company.id}
        )
        self.env["account.fiscal.position.l10n_ar_tax"].create(
            [
                {
                    "fiscal_position_id": fiscal_position.id,
                    "default_tax_id": tax.id,
                    "tax_type": "withholding",
                    "webservice": False,
                }
                for tax in taxes
            ]
        )
        return fiscal_position

    def _create_bill(self, price_unit, document_number, tax_ids=None, company=None, partner=None, **vals):
        bill = (
            self.env["account.move"]
            .with_company(company or self.env.company)
            .create(
                {
                    "move_type": "in_invoice",
                    "partner_id": (partner or self.res_partner_adhoc).id,
                    "invoice_date": "2023-01-01",
                    "l10n_latam_document_number": document_number,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "price_unit": price_unit,
                                "tax_ids": [Command.set((tax_ids or self.tax_21_purchase).ids)],
                            }
                        )
                    ],
                    **vals,
                }
            )
        )
        bill.action_post()
        return bill

    def _create_payment(self, bill, tax=None, post=True, journal=None, to_pay_amount=None, amount=None):
        """A supplier payment pro payment of the bill, as the register payment action opens it. With a tax, the
        payment gets a fiscal position that withholds it; without one, it keeps the fiscal position it resolves.
        From a journal in another currency, pass the amount in that currency: the action proposes the debt in the
        company currency, and only the form converts it."""
        context = bill.line_ids.action_register_payment()["context"]
        vals = {"journal_id": (journal or self.bank_journal).id, "date": "2023-01-01"}
        if amount is not None:
            vals["amount"] = amount
        payment = self.env["account.payment"].with_context(**context).create(vals)
        if tax:
            payment.l10n_ar_fiscal_position_id = self._fiscal_position(tax)
        if to_pay_amount is not None:
            # since 20.0 the amount to pay does not move the payment: the user then types the net amount
            with Form(payment) as form:
                form.to_pay_amount = to_pay_amount
            with Form(payment) as form:
                form.withholding_net_amount = to_pay_amount - payment.withholding_amount
        if post:
            payment.action_post()
        return payment

    def _create_delivery_address(self, state):
        """A delivery address of the supplier: it is the one that resolves the fiscal position of the payment."""
        return self.env["res.partner"].create(
            {
                "name": "Supplier %s" % state.name,
                "parent_id": self.res_partner_adhoc.id,
                "type": "delivery",
                "state_id": state.id,
                "country_id": self.env.ref("base.ar").id,
            }
        )

    def _auto_fiscal_position(self, tax, state):
        """A withholding fiscal position applied by itself to the RI suppliers of the state."""
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Withholding %s" % state.name,
                "company_id": self.env.company.id,
                "auto_apply": True,
                "country_id": self.env.ref("base.ar").id,
                "state_ids": [Command.set(state.ids)],
                "l10n_ar_afip_responsibility_type_ids": [Command.set(self.env.ref("l10n_ar.res_IVARI").ids)],
            }
        )
        self.env["account.fiscal.position.l10n_ar_tax"].create(
            {"fiscal_position_id": fiscal_position.id, "default_tax_id": tax.id, "tax_type": "withholding"}
        )
        return fiscal_position

    def _set_partner_aliquot(self, tax, amount):
        """The aliquot registered on the supplier (as a padron leaves it): a copy of the tax, same group."""
        partner_tax = tax.copy({"name": "%s %s%%" % (tax.name, abs(amount)), "amount": amount})
        self.env["l10n_ar.partner.tax"].create({"partner_id": self.res_partner_adhoc.id, "tax_id": partner_tax.id})
        return partner_tax

    def _assert_entry_withholding(self, payment, tax, amount):
        """The posted entry withholds the same as the line: a credit of the amount on the tax line."""
        tax_lines = payment.move_id.line_ids.filtered(lambda x: x.tax_line_id == tax)
        self.assertAlmostEqual(sum(tax_lines.mapped("balance")), -amount, places=2)
        self.assertTrue(payment.move_id.currency_id.is_zero(sum(payment.move_id.line_ids.mapped("balance"))))

    def _assert_withholding(self, payment, tax, base_amount, amount, ref=None):
        line = payment.withholding_line_ids.filtered(lambda x: x.tax_id == tax)
        self.assertEqual(len(line), 1)
        self.assertAlmostEqual(line.base_amount, base_amount, places=2)
        self.assertAlmostEqual(line.amount, amount, places=2)
        if ref is not None:
            self.assertEqual(line.ref, ref)
        return line
