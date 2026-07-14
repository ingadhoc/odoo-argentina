##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, fields
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestApplyWithholdingByPaymentMethod(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_ri
        cls.company.use_payment_pro = True

        # Impuesto de retención + posición fiscal de retención
        cls.wth_tax = cls.env["account.tax"].create(
            {
                "name": "Ret Test PM 3%",
                "amount": 3.0,
                "amount_type": "percent",
                "type_tax_use": "none",
                "company_id": cls.company.id,
                "l10n_ar_tax_type": "iibb_untaxed",
                "l10n_ar_code": "RET_TEST_PM",
            }
        )
        cls.wth_fp = cls.env["account.fiscal.position"].create(
            {
                "name": "FP Retención Test PM",
                "company_id": cls.company.id,
                "l10n_ar_tax_ids": [Command.create({"default_tax_id": cls.wth_tax.id, "tax_type": "withholding"})],
            }
        )
        # Mapeamos la FP al partner para que _get_fiscal_position la resuelva automáticamente
        cls.res_partner_adhoc.property_account_position_id = cls.wth_fp

        # Diario banco con su método de pago saliente (manual, auto-creado)
        cls.bank_journal = cls.env["account.journal"].create(
            {
                "name": "Banco Test PM",
                "type": "bank",
                "code": "BPMT",
                "company_id": cls.company.id,
            }
        )
        cls.out_pml = cls.bank_journal.outbound_payment_method_line_ids[:1]
        assert cls.out_pml, "El diario banco debe tener un método de pago saliente"

        # Diario de compras sin documentos, para armar facturas de proveedor simples
        cls.purchase_journal = cls.env["account.journal"].create(
            {
                "name": "Compras Test PM",
                "type": "purchase",
                "code": "PPMT",
                "company_id": cls.company.id,
                "l10n_latam_use_documents": False,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_payment(self):
        return self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.res_partner_adhoc.id,
                "amount": 1000.0,
                "journal_id": self.bank_journal.id,
                "payment_method_line_id": self.out_pml.id,
            }
        )

    def _vendor_invoice(self, amount=1000.0):
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.res_partner_adhoc.id,
                "invoice_date": fields.Date.today(),
                "journal_id": self.purchase_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": amount,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _register_wizard(self, invoice, mode="automatic"):
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({})
        )
        wizard.journal_id = self.bank_journal
        wizard.payment_method_line_id = self.out_pml
        wizard.fiscal_position_mode = mode
        return wizard

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_field_default_true(self):
        """El campo arranca en True por default en un método de pago nuevo."""
        self.assertTrue(self.out_pml.l10n_ar_apply_withholding)

    def test_payment_applies_withholding_when_flag_true(self):
        """account.payment: con el flag activo se resuelve la posición fiscal de retención."""
        self.out_pml.l10n_ar_apply_withholding = True
        payment = self._new_payment()
        self.assertEqual(payment.l10n_ar_fiscal_position_id, self.wth_fp)

    def test_payment_skips_withholding_when_flag_false(self):
        """account.payment: con el flag desactivado se fuerza la posición fiscal a vacío."""
        self.out_pml.l10n_ar_apply_withholding = False
        payment = self._new_payment()
        self.assertFalse(payment.l10n_ar_fiscal_position_id)
        self.assertFalse(payment.l10n_ar_withholding_line_ids)

    def test_wizard_applies_withholding_when_flag_true(self):
        """account.payment.register: con el flag activo se resuelve la posición fiscal de retención."""
        self.out_pml.l10n_ar_apply_withholding = True
        wizard = self._register_wizard(self._vendor_invoice())
        self.assertEqual(wizard.l10n_ar_fiscal_position_id, self.wth_fp)

    def test_wizard_skips_withholding_when_flag_false(self):
        """account.payment.register: con el flag desactivado se fuerza la posición fiscal a vacío."""
        self.out_pml.l10n_ar_apply_withholding = False
        wizard = self._register_wizard(self._vendor_invoice())
        self.assertFalse(wizard.l10n_ar_fiscal_position_id)

    def test_wizard_flag_false_holds_in_manual_mode(self):
        """La restricción del medio de pago se sostiene al pasar a modo manual (recompute)."""
        self.out_pml.l10n_ar_apply_withholding = False
        wizard = self._register_wizard(self._vendor_invoice())  # automático -> vacío
        self.assertFalse(wizard.l10n_ar_fiscal_position_id)
        # Cambiar a modo manual dispara el recompute; la restricción del método sigue vigente
        wizard.fiscal_position_mode = "manual"
        self.assertFalse(wizard.l10n_ar_fiscal_position_id)

    # ------------------------------------------------------------------
    # Bypass: el campo es compute store + readonly=False (editable a mano).
    # Un write directo no dispara el compute, así que la guarda en create/write
    # debe sostener la restricción igual.
    # ------------------------------------------------------------------

    def test_payment_manual_write_cannot_bypass_flag(self):
        """account.payment: setear la posición fiscal a mano no saltea el flag del método."""
        self.out_pml.l10n_ar_apply_withholding = False
        payment = self._new_payment()
        self.assertFalse(payment.l10n_ar_fiscal_position_id)
        # Escritura manual directa (no está en los depends del compute)
        payment.l10n_ar_fiscal_position_id = self.wth_fp
        self.assertFalse(payment.l10n_ar_fiscal_position_id)
        self.assertFalse(payment.l10n_ar_withholding_line_ids)

    def test_payment_create_with_fiscal_position_cannot_bypass_flag(self):
        """account.payment: pasar la posición fiscal directo en create tampoco saltea el flag."""
        self.out_pml.l10n_ar_apply_withholding = False
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.res_partner_adhoc.id,
                "amount": 1000.0,
                "journal_id": self.bank_journal.id,
                "payment_method_line_id": self.out_pml.id,
                "l10n_ar_fiscal_position_id": self.wth_fp.id,
            }
        )
        self.assertFalse(payment.l10n_ar_fiscal_position_id)

    def test_payment_manual_write_allowed_when_flag_true(self):
        """account.payment: con el flag activo, la edición manual de la posición fiscal se respeta."""
        self.out_pml.l10n_ar_apply_withholding = True
        payment = self._new_payment()
        payment.l10n_ar_fiscal_position_id = self.wth_fp
        self.assertEqual(payment.l10n_ar_fiscal_position_id, self.wth_fp)

    def test_wizard_manual_write_cannot_bypass_flag(self):
        """account.payment.register: elegir la posición fiscal a mano en modo manual no saltea el flag."""
        self.out_pml.l10n_ar_apply_withholding = False
        wizard = self._register_wizard(self._vendor_invoice(), mode="manual")
        wizard.l10n_ar_fiscal_position_id = self.wth_fp
        self.assertFalse(wizard.l10n_ar_fiscal_position_id)

    def test_wizard_manual_created_payment_cannot_bypass_flag(self):
        """El pago creado desde el wizard en modo manual respeta el flag del método
        (el wizard fuerza la FP sobre el pago con un write directo en _create_payments)."""
        self.out_pml.l10n_ar_apply_withholding = False
        wizard = self._register_wizard(self._vendor_invoice(), mode="manual")
        wizard.l10n_ar_fiscal_position_id = self.wth_fp
        payments = wizard._create_payments()
        self.assertFalse(payments.l10n_ar_fiscal_position_id)
        self.assertFalse(payments.l10n_ar_withholding_line_ids)
