from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestTaxOverlap(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.perception = cls.tax_perc_iibb.copy(
            {
                "name": "Perc IIBB Overlap Test 2.5%",
                "amount": 2.5,
                "active": True,
                "l10n_ar_state_id": cls.env.ref("base.state_ar_b").id,
            }
        )

    def _copy_perception(self, **values):
        return self.perception.copy({"name": "Perc IIBB Overlap Test copy", "active": True, **values})

    def test_same_aliquot_and_group_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._copy_perception()

    def test_other_aliquot_is_allowed(self):
        self._copy_perception(amount=3.0)

    def test_other_jurisdiction_is_allowed(self):
        self._copy_perception(l10n_ar_state_id=self.env.ref("base.state_ar_c").id)

    def test_multilateral_variants_are_allowed(self):
        self._copy_perception(l10n_ar_tax_type="iibb_total")
        self._copy_perception(name="Perc IIBB Overlap Test CM", ratio=50.0)

    def test_archived_duplicate_is_allowed_until_reactivated(self):
        duplicated = self._copy_perception(active=False)
        with self.assertRaises(ValidationError):
            duplicated.active = True

    def test_tax_without_jurisdiction_is_not_checked(self):
        self.perception.l10n_ar_state_id = False
        self._copy_perception()

    def test_empty_base_counts_as_net_base(self):
        self.perception.l10n_ar_tax_type = "iibb_untaxed"
        with self.assertRaises(ValidationError):
            self._copy_perception(l10n_ar_tax_type=False)
        self.perception.l10n_ar_tax_type = False
        with self.assertRaises(ValidationError):
            self._copy_perception(l10n_ar_tax_type="iibb_untaxed")

    def test_archived_twin_is_ignored_without_active_test(self):
        self.perception.active = False
        duplicated = self._copy_perception(active=False)
        duplicated.with_context(active_test=False).active = True

    def test_copy_is_archived(self):
        copy = self.perception.copy()
        self.assertFalse(copy.active)

    def _create_withholding_line(self):
        """Padrón withholding line on a net base 0.6% tax, returned with that tax."""
        tax_group = self.env["account.tax.group"].create(
            {"name": "Test Ret. Overlap", "company_id": self.company_ri.id}
        )
        tax = self.env["account.tax"].create(
            {
                "name": "Ret. IIBB Overlap Test 0.6%",
                "amount": 0.6,
                "amount_type": "percent",
                "type_tax_use": "none",
                "sequence": 10,
                "country_id": self.env.ref("base.ar").id,
                "company_id": self.company_ri.id,
                "l10n_ar_withholding_payment_type": "supplier",
                "l10n_ar_tax_type": "iibb_untaxed",
                "l10n_ar_state_id": self.env.ref("base.state_ar_s").id,
                "tax_group_id": tax_group.id,
            }
        )
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Test Overlap",
                "company_id": self.company_ri.id,
                "l10n_ar_tax_ids": [
                    Command.create({"default_tax_id": tax.id, "tax_type": "withholding", "webservice": "padron"})
                ],
            }
        )
        return fiscal_position.l10n_ar_tax_ids, tax

    def test_ensure_tax_prefers_the_active_tax(self):
        line, active_tax = self._create_withholding_line()
        # The archived twin comes first in the default order (sequence, id).
        active_tax.copy({"name": "Ret. IIBB Overlap Test 0.6% old", "active": False, "sequence": 1})
        self.assertEqual(line._ensure_tax(0.6, l10n_ar_tax_type="iibb_untaxed"), active_tax)
