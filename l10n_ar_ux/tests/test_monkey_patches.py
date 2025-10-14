##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from freezegun import freeze_time
from odoo import Command
from odoo.addons.account_followup.tests.test_followup_report import TestAccountFollowupReports


def monkey_patches():
    """
    Apply monkey patches to fix test issues with followup reports.
    """

    def test_followup_lines_branches_patch(self):
        """Patched version of test_followup_lines_branches"""
        branch = self.env["res.company"].create({"name": "branch", "parent_id": self.env.company.id})
        self.cr.precommit.run()  # load the COA

        report = self.env["account.followup.report"]
        options = {
            "partner_id": self.partner_a.id,
        }

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2016-01-01",
                "partner_id": self.partner_a.id,
                "company_id": branch.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "price_unit": 500,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        invoice.action_post()

        self.assertLinesValues(
            report._get_followup_report_lines(options),
            [0, 1, 2, 3, 5],
            [
                ("INV/2016/00001", "01/01/2016", "01/01/2016", "", "USD\xa0500.00"),
                ("", "", "", "", "USD\xa0500.00"),
                ("", "", "", "", "USD\xa0500.00"),
            ],
            options,
        )

    def test_followup_report_with_entries_patch(self):
        """
        Patched version of test_followup_report_with_entries
        Entries shouldn't have a due date or be added to total_overdue on the followup report and on the partner.
        """
        report = self.env["account.followup.report"]
        options = {
            "partner_id": self.partner_a.id,
        }
        with freeze_time("2016-01-02"):
            invoice = self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "invoice_date": "2016-01-01",
                    "invoice_date_due": "2016-01-01",
                    "invoice_payment_term_id": False,
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "quantity": 1,
                                "price_unit": 300,
                                "tax_ids": [],
                            }
                        )
                    ],
                }
            )
            invoice.action_post()

            entry = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "date": "2016-01-02",
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": "line1",
                                "account_id": self.company_data["default_account_receivable"].id,
                                "debit": 500.0,
                                "credit": 0.0,
                                "no_followup": False,
                            }
                        ),
                        Command.create(
                            {
                                "name": "counterpart line",
                                "account_id": self.company_data["default_account_revenue"].id,
                                "debit": 0.0,
                                "credit": 500.0,
                            }
                        ),
                    ],
                }
            )
            entry.action_post()

        with freeze_time("2016-01-15"):
            self.assertLinesValues(
                report._get_followup_report_lines(options),
                [0, 1, 2, 3, 5],
                [
                    ("MISC/2016/01/0001", "01/02/2016", "", "", "USD\xa0500.00"),
                    ("INV/2016/00001", "01/01/2016", "01/01/2016", "", "USD\xa0300.00"),
                    ("", "", "", "", "USD\xa0800.00"),
                    ("", "", "", "", "USD\xa0300.00"),
                ],
                options,
            )
        self.assertEqual(self.partner_a.total_due, 800)
        self.assertEqual(self.partner_a.total_overdue, 300)

    def propagate(method1, method2):
        """Propagate decorators from ``method1`` to ``method2``, and return the
        resulting method.
        """
        if method1:
            for attr in ("_returns",):
                if hasattr(method1, attr) and not hasattr(method2, attr):
                    setattr(method2, attr, getattr(method1, attr))
        return method2

    def _patch_method(cls, method_name, new_method):
        """Método para aplicar monkey patches.
        cls --> clase
        method_name --> nombre del método original
        new_method --> método que tiene el parche
        """
        origin = getattr(cls, method_name)
        new_method.origin = origin
        wrapped = propagate(origin, new_method)
        wrapped.origin = origin
        setattr(cls, method_name, wrapped)

    # Apply patches
    _patch_method(TestAccountFollowupReports, "test_followup_lines_branches", test_followup_lines_branches_patch)
    _patch_method(
        TestAccountFollowupReports,
        "test_followup_report_with_entries",
        test_followup_report_with_entries_patch,
    )
