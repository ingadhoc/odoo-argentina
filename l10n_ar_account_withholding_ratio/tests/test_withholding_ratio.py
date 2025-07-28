from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestL10nArWithholdingArRi
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install", "ratio")
class TestWithholdingRatio(TestL10nArWithholdingArRi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear un impuesto con ratio del 25%
        cls.tax_with_ratio_25 = cls.env["account.tax"].create(
            {
                "name": "Test Tax with Ratio 25%",
                "amount_type": "percent",
                "amount": 15.0,
                "ratio": 25.0,
                "company_id": cls.company_ri.id,
                "l10n_ar_withholding_sequence_id": cls.tax_wth_seq.id,
            }
        )

        # Crear un impuesto con ratio del 100% (caso normal)
        cls.tax_with_ratio_100 = cls.env["account.tax"].create(
            {
                "name": "Test Tax Normal Ratio 100%",
                "amount_type": "percent",
                "amount": 10.0,
                "ratio": 100.0,
                "company_id": cls.company_ri.id,
                "l10n_ar_withholding_sequence_id": cls.tax_wth_seq.id,
            }
        )

        # Crear un impuesto con tipo 'fixed'
        cls.tax_fixed = cls.env["account.tax"].create(
            {
                "name": "Test Tax Fixed",
                "amount_type": "fixed",
                "amount": 100.0,
                "ratio": 50.0,  # Este ratio no debería aplicarse
                "company_id": cls.company_ri.id,
                "l10n_ar_withholding_sequence_id": cls.tax_wth_seq.id,
            }
        )

    def test_compute_base_amount_with_ratio_25(self):
        """Test que el base_amount se calcule correctamente con ratio del 25%"""

        moves = self.in_invoice_wht("2-11")
        taxes = [{"id": self.tax_with_ratio_25.id, "base_amount": sum(moves.mapped("amount_untaxed"))}]

        wizard = self.new_payment_register(moves, taxes)

        # Base original: 1000, con ratio del 25% debería ser 250
        expected_base_amount = 1000.0 * (self.tax_with_ratio_25.ratio / 100)

        self.assertEqual(
            wizard.l10n_ar_withholding_ids.base_amount,
            expected_base_amount,
            f"Con ratio 25% y base 1000, el base_amount debería ser {expected_base_amount}",
        )

        # Verificar que el amount también se calcule correctamente (15% de 250 = 37.5)
        expected_amount = expected_base_amount * (self.tax_with_ratio_25.amount / 100)
        self.assertEqual(
            wizard.l10n_ar_withholding_ids.amount,
            expected_amount,
            f"Con ratio 25% y tasa 15%, el amount debería ser {expected_amount}",
        )

    def test_compute_base_amount_with_ratio_100(self):
        """Test que el base_amount no se modifique con ratio del 100%"""

        moves = self.in_invoice_wht("2-12")
        taxes = [{"id": self.tax_with_ratio_100.id, "base_amount": sum(moves.mapped("amount_untaxed"))}]

        wizard = self.new_payment_register(moves, taxes)

        # Con ratio del 100%, el base_amount no debería modificarse
        original_base_amount = 1000.0

        self.assertEqual(
            wizard.l10n_ar_withholding_ids.base_amount,
            original_base_amount,
            "El base_amount no debería haberse modificado con ratio 100%",
        )

    def test_compute_base_amount_with_non_percent_tax(self):
        """Test que el ratio no se aplique a impuestos que no son de tipo 'percent'"""

        moves = self.in_invoice_wht("2-13")
        taxes = [{"id": self.tax_fixed.id, "base_amount": sum(moves.mapped("amount_untaxed"))}]
        # El base_amount NO debería modificarse porque el impuesto no es de tipo 'percent'
        original_base_amount = 1000.0
        wizard = self.new_payment_register(moves, taxes)

        self.assertEqual(
            wizard.l10n_ar_withholding_ids.base_amount,
            original_base_amount,
            "El ratio no debería aplicarse a impuestos que no son de tipo 'percent'",
        )
