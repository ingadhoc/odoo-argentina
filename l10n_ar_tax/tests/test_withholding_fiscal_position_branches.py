from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestWithholdingFiscalPositionBranches(TestArCommon):
    """A vendor payment of a branch only offers the parent's withholding positions shared with it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent = cls.company_ri
        cls.same_entity_branch = cls.env["res.company"].create(
            {"name": "Branch same Tax ID", "parent_id": cls.parent.id, "vat": cls.parent.vat}
        )
        cls.auxiliary_branch = cls.env["res.company"].create({"name": "Auxiliary", "parent_id": cls.parent.id})
        cls.env.user.company_ids |= cls.same_entity_branch | cls.auxiliary_branch

        tax = cls.env["account.tax"].search(
            [("company_id", "=", cls.parent.id), ("l10n_ar_withholding_payment_type", "=", "supplier")], limit=1
        )
        cls.positions = {
            scope: cls.env["account.fiscal.position"].create(
                {
                    "name": f"Withholding {scope}",
                    "company_id": cls.parent.id,
                    "shared_to_branches": scope,
                    "l10n_ar_tax_ids": [Command.create({"default_tax_id": tax.id, "tax_type": "withholding"})],
                }
            )
            for scope in ("all", "legal_entity", "none")
        }

    def _allowed_scopes(self, company):
        payment = self.env["account.payment"].new(
            {"company_id": company.id, "payment_type": "outbound", "partner_type": "supplier"}
        )
        allowed = payment.l10n_ar_allowed_fiscal_position_ids._origin
        return {scope for scope, position in self.positions.items() if position in allowed}

    def test_allowed_positions_follow_shared_to_branches(self):
        self.assertEqual(self._allowed_scopes(self.parent), {"all", "legal_entity", "none"})
        self.assertEqual(self._allowed_scopes(self.same_entity_branch), {"all", "legal_entity"})
        self.assertEqual(self._allowed_scopes(self.auxiliary_branch), {"all"})
