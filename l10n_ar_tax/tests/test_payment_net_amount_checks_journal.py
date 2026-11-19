from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import Form, tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPaymentNetAmountChecksJournal(TestArWithholdingArRi):
    """A vendor payment opened from the bill with a third party checks journal
    kept the gross amount (withholdings added on top) when the journal was changed afterwards."""

    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.bank_journal = self.env["account.journal"].search(
            [("company_id", "=", self.company_ri.id), ("type", "=", "bank")], limit=1
        )
        self.check_journal = self.third_party_check_journal()
        # CABA delivery address under the RI partner: it triggers the IIBB CABA withholding position
        partner = self.env["res.partner"].create(
            {
                "name": "Vendor CABA 133451",
                "parent_id": self.res_partner_adhoc.id,
                "type": "delivery",
                "state_id": self.env.ref("base.state_ar_c").id,
                "country_id": self.env.ref("base.ar").id,
            }
        )
        wth_tax = self.tax_wth_test_1.copy({"name": "IIBB WTH CABA 2.5%", "amount": 2.5})
        self.env["l10n_ar.partner.tax"].create({"partner_id": self.res_partner_adhoc.id, "tax_id": wth_tax.id})
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "IIBB CABA",
                "auto_apply": True,
                "sequence": 10,
                "company_id": self.company_ri.id,
                "l10n_ar_afip_responsibility_type_ids": [Command.set(self.env.ref("l10n_ar.res_IVARI").ids)],
                "country_id": self.env.ref("base.ar").id,
                "state_ids": [Command.set(self.env.ref("base.state_ar_c").ids)],
            }
        )
        self.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": fiscal_position.id,
                "default_tax_id": self.tax_wth_test_1.id,
                "tax_type": "withholding",
            }
        )
        # net 500.000 + VAT 21% = 605.000; withholding 2.5% of the net = 12.500
        self.bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "company_id": self.company_ri.id,
                "invoice_date": self.today,
                "l10n_latam_document_number": "1-133451",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 500000,
                            "tax_ids": [Command.set(self.tax_21.ids)],
                        }
                    )
                ],
            }
        )
        self.bill.action_post()

    def _payment_form(self, journal):
        context = self.bill.action_register_payment()["context"]
        return Form(self.env["account.payment"].with_context(**context, default_journal_id=journal.id))

    def test_opened_with_checks_journal_then_cash(self):
        # l10n_ar_payment_bundle recomputes the amount on withholdings change, which l10n_latam_check sets to 0
        if self.env["ir.module.module"]._get("l10n_ar_payment_bundle").state == "installed":
            self.skipTest("l10n_ar_payment_bundle sets the amount of a check payment without checks to 0")
        form = self._payment_form(self.check_journal)
        self.assertEqual(form.payment_method_code, "out_third_party_checks")
        self.assertEqual(form.withholdings_amount, 12500)
        self.assertEqual(form.amount, 592500, "Without checks selected the proposed amount is the net")

        form.journal_id = self.bank_journal

        self.assertEqual(form.amount, 592500)
        self.assertEqual(form.payment_difference, 0)

    def test_selected_checks_keep_the_amount(self):
        check = self.in_third_party_check(self.check_journal).l10n_latam_new_check_ids
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.res_partner_adhoc.id,
                "journal_id": self.check_journal.id,
                "payment_method_line_id": self.check_journal.outbound_payment_method_line_ids[0].id,
                "l10n_latam_move_check_ids": [Command.set(check.ids)],
            }
        )
        self.assertEqual(payment.amount, check.amount)

        payment._onchange_withholdings()

        self.assertEqual(payment.amount, check.amount, "With checks selected the amount is the checks total")
