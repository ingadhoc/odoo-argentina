from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestFiscalPositionResponsibilityMatch(TestArCommon):
    """A fiscal position without ARCA responsibility types is not applied by itself, as in 19.0 (only AR Domestic)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.state_ba = cls.env.ref("base.state_ar_b")
        cls.partner_cf_ba = cls.env["res.partner"].create(
            {
                "name": "Final consumer Buenos Aires",
                "country_id": cls.env.ref("base.ar").id,
                "state_id": cls.state_ba.id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_CF").id,
            }
        )
        cls.domestic_fp = cls.env["account.chart.template"].ref("l10n_ar_domestic_fiscal_position")

    def _perception_fp(self, responsibility_types):
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Perception Buenos Aires",
                "company_id": self.env.company.id,
                "auto_apply": True,
                "sequence": 1,
                "country_id": self.env.ref("base.ar").id,
                "state_ids": [Command.set(self.state_ba.ids)],
                "l10n_ar_afip_responsibility_type_ids": [Command.set(responsibility_types.ids)],
            }
        )
        self.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": fiscal_position.id,
                "default_tax_id": self.tax_perc_iibb.id,
                "tax_type": "perception",
            }
        )
        return fiscal_position

    def test_without_responsibility_types_not_applied(self):
        perception_fp = self._perception_fp(self.env["l10n_ar.afip.responsibility.type"])
        fiscal_position = self.env["account.fiscal.position"]._get_fiscal_position(self.partner_cf_ba)
        self.assertNotEqual(fiscal_position, perception_fp)
        self.assertEqual(fiscal_position, self.domestic_fp)

    def test_with_responsibility_type_applied(self):
        perception_fp = self._perception_fp(self.env.ref("l10n_ar.res_CF"))
        fiscal_position = self.env["account.fiscal.position"]._get_fiscal_position(self.partner_cf_ba)
        self.assertEqual(fiscal_position, perception_fp)
