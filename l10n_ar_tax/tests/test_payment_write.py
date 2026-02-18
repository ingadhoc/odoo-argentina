from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPaymentWrite(TestArWithholdingArRi):
    """Tests para validar que al modificar un pago se actualicen correctamente los apuntes contables."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Instalar demo data dinámica
        chart_template = cls.env["account.chart.template"]
        chart_template._install_l10n_ar_tax_demo(cls.company_ri)

        # Referenciar demo data creada dinámicamente
        cls.invoice_1 = chart_template.ref("demo_vendor_bill_caba_1")
        cls.invoice_2 = chart_template.ref("demo_vendor_bill_caba_2")
        cls.payment_1 = chart_template.ref("demo_payment_only_withholdings")
        cls.payment_2 = chart_template.ref("demo_payment_to_edit")

    def test_01_payment_with_only_withholdings_no_liquidity(self):
        """Test pago sin amount (solo retenciones).

        1. Usar payment de demo data (amount = 0)
        2. Post payment
        3. VALIDATION: No debe existir línea de liquidez
        4. VALIDATION: Deben existir líneas de retención
        5. VALIDATION: Debe existir línea de deuda (counterpart)
        """
        payment = self.payment_1

        # Post payment
        payment.action_post()

        # VALIDATION: No debe existir línea de liquidez (amount es 0)
        liquidity_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id == payment.journal_id.default_account_id
        )
        self.assertFalse(liquidity_lines, "Liquidity line should not exist when payment amount is zero")

        # VALIDATION: Deben existir líneas de retención
        withholding_lines = payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id)
        self.assertTrue(withholding_lines, "Withholding lines should be created even with zero payment amount")

        # VALIDATION: Debe existir línea de deuda (counterpart)
        receivable_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
        self.assertTrue(receivable_lines, "Counterpart debt line should exist")
        self.assertGreater(sum(receivable_lines.mapped("debit")), 0, "Counterpart line should have positive debit")

        # VALIDATION: El asiento debe estar balanceado
        total_balance = sum(payment.move_id.line_ids.mapped("balance"))
        self.assertAlmostEqual(total_balance, 0.0, places=2, msg="Move should be balanced")

    def test_02_payment_edit_updates_accounting_entries(self):
        """Test edición de pago actualiza apuntes contables.

        1. Usar payment de demo data con amount
        2. Post payment y guardar valores originales
        3. Editar payment (cambiar amount)
        4. VALIDATION: Las líneas del move deben actualizarse
        5. VALIDATION: Los nuevos balances deben reflejar el nuevo amount
        6. VALIDATION: El asiento debe seguir balanceado
        """
        payment = self.payment_2

        # Post payment
        payment.action_post()

        # Guardar valores originales
        original_liquidity_balance = sum(
            payment.move_id.line_ids.filtered(lambda l: l.account_id == payment.journal_id.default_account_id).mapped(
                "balance"
            )
        )
        original_withholding_balance = sum(
            payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id).mapped("balance")
        )

        # Editar payment: cambiar amount
        payment.write({"amount": 100000})

        # VALIDATION: Las líneas del move deben actualizarse
        new_liquidity_balance = sum(
            payment.move_id.line_ids.filtered(lambda l: l.account_id == payment.journal_id.default_account_id).mapped(
                "balance"
            )
        )
        new_withholding_balance = sum(
            payment.move_id.line_ids.filtered(lambda l: l.tax_repartition_line_id).mapped("balance")
        )

        self.assertNotEqual(
            original_liquidity_balance,
            new_liquidity_balance,
            "Liquidity line should be updated after payment amount change",
        )
        self.assertNotEqual(
            original_withholding_balance,
            new_withholding_balance,
            "Withholding lines should be updated after payment amount change",
        )

        # VALIDATION: Los nuevos balances deben reflejar el nuevo amount
        # Withholding es 10% del base amount
        expected_withholding_amount = -10000  # 10% of 100000
        self.assertAlmostEqual(
            new_withholding_balance,
            expected_withholding_amount,
            places=2,
            msg="Withholding amount should be 10% of new payment amount",
        )

        # VALIDATION: El asiento debe seguir balanceado
        total_balance = sum(payment.move_id.line_ids.mapped("balance"))
        self.assertAlmostEqual(total_balance, 0.0, places=2, msg="Move should remain balanced after edit")

    def test_03_payment_edit_with_amount_withholding_and_writeoff(self):
        """Test edición de pago con amount, retenciones y write-off.

        1. Copiar payment de demo y modificar amount
        2. Post payment
        3. Editar amount a un valor aún menor
        4. VALIDATION: Todas las líneas deben actualizarse (liquidity, withholding, write-off, counterpart)
        5. VALIDATION: El asiento debe seguir balanceado
        """
        # Copiar payment para no afectar otros tests
        payment = self.payment_2.copy({"amount": 180000})

        # Post payment
        payment.action_post()

        # Contar líneas originales
        original_line_count = len(payment.move_id.line_ids)

        # Editar payment: reducir más el amount
        payment.write({"amount": 120000})

        # VALIDATION: El número de líneas debería ser similar (pueden variar ligeramente)
        new_line_count = len(payment.move_id.line_ids)
        self.assertTrue(
            abs(original_line_count - new_line_count) <= 2,
            f"Line count should remain similar. Original: {original_line_count}, New: {new_line_count}",
        )

        # VALIDATION: El asiento debe seguir balanceado
        total_balance = sum(payment.move_id.line_ids.mapped("balance"))
        self.assertAlmostEqual(
            total_balance, 0.0, places=2, msg="Move should remain balanced after edit with write-off"
        )

        # VALIDATION: Debe existir línea de liquidez
        liquidity_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id == payment.journal_id.default_account_id
        )
        self.assertTrue(liquidity_lines, "Liquidity line should exist")

        # VALIDATION: El balance de liquidez debe ser negativo (pago saliente)
        liquidity_balance = sum(liquidity_lines.mapped("balance"))
        self.assertLess(liquidity_balance, 0, "Liquidity balance should be negative for outbound payment")
