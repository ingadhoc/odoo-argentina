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
        return self.perception.copy({"name": "Perc IIBB Overlap Test copy", **values})

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
