##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, fields
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestPaymentRegisterProWizard(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.company = cls.env.company
        cls.company.use_payment_pro = True
        # Pre-existing companies lack batch_payment_sequence_id (the field default
        # only fires on company create), so multi-partner batch communication
        # crashes on next_by_id() over an empty sequence. Ensure it here.
        if not cls.company.batch_payment_sequence_id:
            cls.company.batch_payment_sequence_id = (
                cls.env["ir.sequence"]
                .sudo()
                .create(
                    {
                        "name": "Group Payments Number Sequence",
                        "implementation": "no_gap",
                        "padding": 5,
                        "use_date_range": True,
                        "company_id": cls.company.id,
                        "prefix": "GROUP/%(year)s/",
                    }
                )
            )
        cls.company_journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.company.id), ("type", "=", "sale")], limit=1
        )
        cls.partner_ri = cls.env["res.partner"].create(
            dict(name="RI Partner", vat="34278580484", country_id=cls.env.ref("base.ar").id)
        )

    def _make_invoice(self, partner, amount=100):
        inv = self.env["account.move"].create(
            {
                "partner_id": partner.id,
                "invoice_date": self.today,
                "move_type": "out_invoice",
                "journal_id": self.company_journal.id,
                "company_id": self.company.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.env.ref("product.product_product_16").id,
                            "quantity": 1,
                            "price_unit": amount,
                        }
                    )
                ],
            }
        )
        inv.action_post()
        return inv

    def test_action_register_payment_single_partner_opens_account_payment(self):
        """Single partner: action_register_payment should open `account.payment` form."""
        invoice = self._make_invoice(self.partner_ri, 120)
        action = invoice.action_register_payment()
        self.assertEqual(action.get("res_model"), "account.payment")
        self.assertEqual(action.get("target"), "current")
        ctx = action.get("context") or {}
        self.assertIn("default_to_pay_move_line_ids", ctx)
        self.assertTrue(ctx.get("default_to_pay_move_line_ids"))

    def test_action_register_payment_multiple_partners_opens_register_wizard(self):
        """Multiple partners: should open `account.payment.register` wizard with `payment_pro` context."""
        partner_other = self.env.ref("base.res_partner_12")
        invoice_1 = self._make_invoice(self.partner_ri, 50)
        invoice_2 = self._make_invoice(partner_other, 75)

        action = (invoice_1 + invoice_2).line_ids.action_register_payment()
        self.assertEqual(action.get("res_model"), "account.payment.register")
        self.assertEqual(action.get("target"), "new")
        ctx = action.get("context") or {}
        self.assertTrue(ctx.get("payment_pro"))
        self.assertIn("active_ids", ctx)
        self.assertTrue(ctx.get("active_ids"))

    def test_create_payments_and_grouping(self):
        """Create payments from register wizard and assert payments are posted and grouped per partner when enabled."""
        partner_other = self.env.ref("base.res_partner_12")
        invoices = self.env["account.move"]
        amounts = [30, 40, 50, 60]
        partners = [self.partner_ri, self.partner_ri, partner_other, partner_other]
        for amt, partner in zip(amounts, partners):
            invoices |= self._make_invoice(partner, amt)

        action = invoices.line_ids.action_register_payment()
        ctx = action.get("context") or {}
        wiz = self.env["account.payment.register"].with_context(**ctx).create({})

        payments = wiz._create_payments()
        payments = self.env["account.payment"].browse(payments.ids if hasattr(payments, "ids") else [])

        self.assertTrue(payments, "Payments should be created")
        for p in payments:
            self.assertIn(p.state, ["posted", "in_process", "paid"], "Payment should be posted or paid")

        # Test grouping
        invoices2 = self.env["account.move"]
        for amt, partner in zip([10, 20, 30, 40], [self.partner_ri, self.partner_ri, partner_other, partner_other]):
            invoices2 |= self._make_invoice(partner, amt)

        action2 = invoices2.line_ids.action_register_payment()
        ctx2 = action2.get("context") or {}
        wiz2 = self.env["account.payment.register"].with_context(**ctx2).create({})
        if hasattr(wiz2, "group_payment"):
            wiz2.group_payment = True
        else:
            wiz2 = self.env["account.payment.register"].with_context(**{**ctx2, "group_payment": True}).create({})

        payments2 = wiz2._create_payments()
        payments2 = self.env["account.payment"].browse(payments2.ids if hasattr(payments2, "ids") else [])
        self.assertTrue(payments2, "Payments should be created when grouping")

        partners_created = payments2.mapped("partner_id")
        self.assertEqual(len(payments2), len(partners_created), "There should be one payment per partner when grouping")
