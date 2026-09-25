from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestPerceptionSantaFeRatio(TestArCommon):
    """Percepción de Santa Fe con ratio 50 (Convenio Multilateral), alícuota 3%."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        perception_group = cls.env.ref(
            "account.%i_ri_tax_percepcion_iibb_caba_aplicada" % cls.env.company.id
        ).tax_group_id
        cls.perception_tax = cls.env["account.tax"].create(
            {
                "name": "Test Percepción IIBB SF 3% CM",
                "amount": 3.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "country_id": cls.env.ref("base.ar").id,
                "company_id": cls.company_ri.id,
                "l10n_ar_state_id": cls.env.ref("base.state_ar_s").id,
                "tax_group_id": perception_group.id,
                "ratio": 50.0,
            }
        )

    def _post_invoice(self, price_unit):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.res_partner_adhoc.id,
                "company_id": self.company_ri.id,
                "invoice_date": "2025-01-15",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.service_iva_21.id,
                            "price_unit": price_unit,
                            "tax_ids": [Command.set((self.tax_21 + self.perception_tax).ids)],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice.line_ids.filtered(lambda line: line.tax_line_id == self.perception_tax)

    def test_01_perceives_on_half_of_the_base(self):
        """100000 * 50% * 3% = 1500, con base informada 50000."""
        line = self._post_invoice(100000.0)
        self.assertAlmostEqual(abs(line.balance), 1500.0, places=2)
        self.assertAlmostEqual(abs(line.tax_base_amount), 50000.0, places=2)

    def test_02_ratio_ignored_outside_santa_fe(self):
        """Fuera de Santa Fe el ratio no tiene efecto: 100000 * 3% = 3000."""
        self.perception_tax.l10n_ar_state_id = self.env.ref("base.state_ar_c")
        self.assertAlmostEqual(abs(self._post_invoice(100000.0).balance), 3000.0, places=2)

    def test_03_minimum_base_applies_to_the_full_base(self):
        """La base mínima de 360000 se compara contra la base completa, no contra la mitad."""
        self.perception_tax.l10n_ar_base_minimum_threshold = 360000
        self.assertAlmostEqual(abs(self._post_invoice(360000.0).balance), 0.0, places=2)
        self.assertAlmostEqual(abs(self._post_invoice(400000.0).balance), 6000.0, places=2)
