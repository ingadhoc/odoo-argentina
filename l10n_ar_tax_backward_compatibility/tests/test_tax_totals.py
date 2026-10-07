from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestInactiveTaxTotals(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.company_data["company"]
        cls.tax_group = cls.env["account.tax.group"].create(
            {"name": "VAT backward compatibility", "company_id": company.id}
        )
        tax_values = {
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 21.0,
            "tax_group_id": cls.tax_group.id,
            "company_id": company.id,
        }
        cls.tax_current = cls.env["account.tax"].create(dict(tax_values, name="VAT 21 current"))
        cls.tax_archived = cls.env["account.tax"].create(dict(tax_values, name="VAT 21 archived"))
        cls.tax_archived.active = False

    def _create_invoice(self, lines):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2024-01-01",
                "date": "2024-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": name,
                            "quantity": 1,
                            "price_unit": price,
                            "tax_ids": [Command.set(tax.ids)],
                        }
                    )
                    for name, price, tax in lines
                ],
            }
        )

    def test_mixed_group_keeps_the_active_tax_amount(self):
        """A group mixing an archived tax and the active one that replaced it must
        show the whole amount, not only the archived part."""
        invoice = self._create_invoice(
            [
                ("current tax", 1000.0, self.tax_current),
                ("archived tax", 500.0, self.tax_archived),
            ]
        )
        invoice.action_post()

        self.assertEqual(invoice.amount_tax, 315.0)
        self.assertAlmostEqual(invoice.tax_totals["tax_amount_currency"], invoice.amount_tax)
        self.assertAlmostEqual(invoice.tax_totals["total_amount_currency"], invoice.amount_total)

    def test_group_with_only_archived_taxes(self):
        """The replacement still covers the case it was written for."""
        invoice = self._create_invoice([("archived tax", 500.0, self.tax_archived)])
        invoice.action_post()

        self.assertEqual(invoice.amount_tax, 105.0)
        self.assertAlmostEqual(invoice.tax_totals["tax_amount_currency"], invoice.amount_tax)
