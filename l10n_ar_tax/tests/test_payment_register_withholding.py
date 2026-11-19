from odoo.tests import tagged

from .common import L10nArTaxPaymentCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPaymentRegisterWithholding(L10nArTaxPaymentCommon):
    """The bulk payment of bills of several suppliers, the only use of the register wizard with payment pro: each
    payment proposes its own withholdings, over the debt it pays, as a payment registered from one bill."""

    def test_bulk_payment_of_two_suppliers_withholds_each_one(self):
        caba = self.env.ref("base.state_ar_c")
        fiscal_position = self._auto_fiscal_position(self.tax_iibb_untaxed, caba)
        # no AGIP lookup and no aliquot of their own: both suppliers are withheld at the 3% of the tax
        fiscal_position.l10n_ar_tax_ids.webservice = False
        supplier_1, supplier_2 = (
            self.env["res.partner"].create(
                {
                    "name": name,
                    "vat": vat,
                    "l10n_ar_afip_responsibility_type_id": self.env.ref("l10n_ar.res_IVARI").id,
                    "country_id": self.env.ref("base.ar").id,
                    "state_id": caba.id,
                }
            )
            for name, vat in (("First RI supplier", "30700000016"), ("Second RI supplier", "30711111111"))
        )
        bills = self._create_bill(1000.0, "1-1", partner=supplier_1) + self._create_bill(
            2000.0, "1-2", partner=supplier_2
        )

        action = bills.line_ids.action_register_payment()
        self.assertEqual(action["res_model"], "account.payment.register")
        wizard = (
            self.env["account.payment.register"]
            .with_context(**action["context"])
            .create({"journal_id": self.bank_journal.id, "payment_date": "2023-01-01"})
        )
        payments = wizard._create_payments()
        self.assertEqual(len(payments), 2)
        for supplier, base, withholding in ((supplier_1, 1000.0, 30.0), (supplier_2, 2000.0, 60.0)):
            payment = payments.filtered(lambda x: x.partner_id == supplier)
            self.assertNotEqual(payment.state, "draft")
            self._assert_withholding(payment, self.tax_iibb_untaxed, base, withholding)
            self._assert_entry_withholding(payment, self.tax_iibb_untaxed, withholding)
            self.assertAlmostEqual(payment.amount, base * 1.21, places=2)
            self.assertAlmostEqual(payment.withholding_net_amount, base * 1.21 - withholding, places=2)
        self.assertTrue(all(bill.currency_id.is_zero(bill.amount_residual) for bill in bills))
