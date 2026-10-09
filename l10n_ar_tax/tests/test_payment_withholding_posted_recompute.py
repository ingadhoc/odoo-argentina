from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPaymentWithholdingPostedRecompute(TestArWithholdingArRi):
    """The withholdings of a posted payment keep their base and amount when something forces their recompute.

    Case: an invoice is paid one cent short and a second payment pays that cent. The first payment carries a
    negative advance (-0.01) and the invoice residual is 0 by now, so recomputing its withholding base used to
    raise the "selected debt" UserError (and, without the advance, to rewrite the base from the current residual).
    """

    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.company_bank_journal = self.env["account.journal"].search(
            [("company_id", "=", self.company_ri.id), ("type", "=", "bank")], limit=1
        )
        self.wth_partner = self.env["res.partner"].create(
            {
                "name": "Proveedor CABA",
                "parent_id": self.res_partner_adhoc.id,
                "type": "delivery",
                "state_id": self.env.ref("base.state_ar_c").id,
                "country_id": self.env.ref("base.ar").id,
            }
        )
        wth_tax_caba = self.tax_wth_test_1.copy({"name": "IIBB WTH CABA 2.5%", "amount": 2.5})
        self.env["l10n_ar.partner.tax"].create({"partner_id": self.res_partner_adhoc.id, "tax_id": wth_tax_caba.id})
        fiscal_pos = self.env["account.fiscal.position"].create(
            {
                "name": "IIBB CABA",
                "l10n_ar_afip_responsibility_type_ids": [Command.set(self.env.ref("l10n_ar.res_IVARI").ids)],
                "auto_apply": True,
                "country_id": self.env.ref("base.ar").id,
                "company_id": self.company_ri.id,
                "state_ids": [Command.set(self.env.ref("base.state_ar_c").ids)],
            }
        )
        self.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": fiscal_pos.id,
                "default_tax_id": self.tax_wth_test_1.id,
                "tax_type": "withholding",
            }
        )

    def _register_payment(self, invoice, to_pay_amount):
        action_context = invoice.action_register_payment()["context"]
        payment = (
            self.env["account.payment"]
            .with_context(**action_context)
            .create({"journal_id": self.company_bank_journal.id, "date": self.today})
        )
        payment.to_pay_amount = to_pay_amount
        # the form adjusts the amount through onchange; here it is set as the user would leave it
        payment.amount = payment.to_pay_amount - payment.withholdings_amount
        payment.action_post()
        return payment

    def test_posted_partial_payment_keeps_withholding_on_recompute(self):
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.wth_partner.id,
                "move_type": "in_invoice",
                "company_id": self.company_ri.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 500000,
                            "tax_ids": [Command.set(self.tax_21.ids)],
                        }
                    ),
                ],
                "invoice_date": self.today,
                "l10n_latam_document_number": "1-130058",
            }
        )
        invoice.action_post()

        partial_payment = self._register_payment(invoice, invoice.amount_total - 0.01)
        wth_line = partial_payment.l10n_ar_withholding_line_ids
        self.assertTrue(wth_line, "The partial payment must carry the withholding line.")
        self.assertAlmostEqual(partial_payment.withholdable_advanced_amount, -0.01)
        base_amount, amount = wth_line.base_amount, wth_line.amount

        self._register_payment(invoice, invoice.amount_residual)
        self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))

        # what a raw SQL re-map does from an upgrade script: flag the dependents of tax_id and flush them
        wth_line.modified(["tax_id"])
        self.env.flush_all()

        self.assertEqual(wth_line.base_amount, base_amount)
        self.assertEqual(wth_line.amount, amount)
