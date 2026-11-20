from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestTaxGroupJurisdictionSequence(TestArCommon):
    """Jurisdiction and withholding sequence live in the tax group; AR taxes read them from there."""

    def _ref(self, xmlid):
        return self.env.ref("account.%i_%s" % (self.company_ri.id, xmlid))

    def test_01_chart_fills_the_groups(self):
        """A new AR company gets jurisdiction and sequence on its groups, and the taxes take them."""
        caba = self.env.ref("base.state_ar_c")
        applied = self._ref("ex_tax_withholding_iibb_caba_applied")
        incurred = self._ref("base_tax_withholding_iibb_caba_incurred")
        self.assertEqual(applied.tax_group_id, incurred.tax_group_id)
        group = applied.tax_group_id
        self.assertEqual(group.l10n_ar_state_id, caba)
        self.assertTrue(group.withholding_sequence_id)
        self.assertEqual(applied.l10n_ar_state_id, caba)
        self.assertEqual(applied.withholding_sequence_id, group.withholding_sequence_id)
        with self.subTest("the customer withholding of the same group has no sequence"):
            self.assertEqual(incurred.l10n_ar_state_id, caba)
            self.assertFalse(incurred.withholding_sequence_id)
        with self.subTest("earnings withholdings share the sequence of their group"):
            earnings = self._ref("ex_tax_withholding_profits_regimen_19_insc")
            self.assertTrue(earnings.tax_group_id.withholding_sequence_id)
            self.assertEqual(earnings.withholding_sequence_id, earnings.tax_group_id.withholding_sequence_id)
            self.assertFalse(earnings.l10n_ar_state_id)
        with self.subTest("perceptions take the jurisdiction of their group"):
            perception = self._ref("ri_tax_percepcion_iibb_caba_aplicada")
            self.assertEqual(perception.tax_group_id.l10n_ar_state_id, caba)
            self.assertEqual(perception.l10n_ar_state_id, caba)

    def test_02_group_changes_reach_its_taxes(self):
        applied = self._ref("ex_tax_withholding_iibb_caba_applied")
        incurred = self._ref("base_tax_withholding_iibb_caba_incurred")
        sequence = self.env["ir.sequence"].create({"name": "Test group sequence", "company_id": self.company_ri.id})
        applied.tax_group_id.write(
            {"withholding_sequence_id": sequence.id, "l10n_ar_state_id": self.env.ref("base.state_ar_b").id}
        )
        self.assertEqual(applied.withholding_sequence_id, sequence)
        self.assertEqual(applied.l10n_ar_state_id, self.env.ref("base.state_ar_b"))
        self.assertEqual(incurred.l10n_ar_state_id, self.env.ref("base.state_ar_b"))
        self.assertFalse(incurred.withholding_sequence_id)

    def test_03_a_copied_tax_keeps_the_group_values(self):
        applied = self._ref("ex_tax_withholding_iibb_caba_applied")
        copy = applied.copy()
        self.assertEqual(copy.withholding_sequence_id, applied.withholding_sequence_id)
        self.assertEqual(copy.l10n_ar_state_id, applied.l10n_ar_state_id)

    def test_04_taxes_of_other_countries_keep_their_sequence(self):
        sequence = self.env["ir.sequence"].create({"name": "Test foreign sequence"})
        group = self.env["account.tax.group"].create(
            {"name": "Foreign group", "country_id": self.env.ref("base.us").id}
        )
        tax = self.env["account.tax"].create(
            {
                "name": "Foreign withholding",
                "amount": -1.0,
                "type_tax_use": "purchase",
                "is_withholding_tax": True,
                "country_id": self.env.ref("base.us").id,
                "tax_group_id": group.id,
                "withholding_sequence_id": sequence.id,
            }
        )
        self.assertEqual(tax.withholding_sequence_id, sequence)
        # changing the group recomputes the field: a foreign tax keeps its own value
        tax.tax_group_id = group.copy()
        self.assertEqual(tax.withholding_sequence_id, sequence)
