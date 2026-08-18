from odoo import Command
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestNeuquenMinimum(TestArWithholdingArRi):
    """Tests de aceptación del mínimo sujeto a retención de IIBB Neuquén.

    En Neuquén el mínimo (campo "Minimum Base" / ``l10n_ar_base_minimum_threshold``) se
    evalúa por comprobante: se compara contra el neto de CADA factura, no contra la suma
    de las bases (Res. Gral. 276/DPR/17, art. 10). El módulo solo cambia el caso de pago
    de 2+ facturas; los pagos de una sola factura quedan como el comportamiento nativo.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.neuquen = cls.env.ref("base.state_ar_q")
        cls.wth_seq_nqn = cls.env["ir.sequence"].create(
            {"implementation": "standard", "name": "wth neuquen test", "padding": 8, "number_increment": 1}
        )
        cls.tax_iibb_nqn = cls.tax_wth_test_1.copy(
            default={
                "name": "IIBB Neuquén 2%",
                "amount": 2,
                "l10n_ar_tax_type": "iibb_untaxed",
                "l10n_ar_state_id": cls.neuquen.id,
                "l10n_ar_withholding_sequence_id": cls.wth_seq_nqn.id,
                "l10n_ar_non_taxable_amount": 0,
                "l10n_ar_payment_minimum_threshold": 0,
                "l10n_ar_base_minimum_threshold": 300000,
                "l10n_ar_minimum_threshold": 0,
            }
        )
        # Control: misma config pero sin jurisdicción Neuquén
        cls.tax_iibb_no_nqn = cls.tax_iibb_nqn.copy(
            default={"name": "IIBB Otra Jurisdicción 2%", "l10n_ar_state_id": False}
        )

    def _make_vendor_invoice(self, price_unit, doc_number):
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "date": "2023-01-01",
                "invoice_date": "2023-01-01",
                "partner_id": self.res_partner_adhoc.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": price_unit,
                            "tax_ids": [Command.set(self.tax_21.ids)],
                        }
                    )
                ],
                "l10n_latam_document_number": doc_number,
            }
        )
        invoice.action_post()
        return invoice

    def _withholding_for(self, invoices, tax):
        """Crea un pago que cancela `invoices` y su línea de retención `tax`, dejando que
        base_amount se calcule desde to_pay_move_line_ids (sin fijarlo a mano)."""
        payable_lines = invoices.line_ids.filtered(lambda l: l.account_type == "liability_payable")
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": invoices[0].partner_id.id,
                "amount": sum(invoices.mapped("amount_total")),
                "date": "2023-01-01",
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        payment.to_pay_move_line_ids = [Command.set(payable_lines.ids)]
        wth = self.env["l10n_ar.payment.withholding"].create({"payment_id": payment.id, "tax_id": tax.id})
        return wth

    # ─── Caso 3: pago de 2+ facturas → mínimo por factura, no sobre la suma ─────

    def test_01_neuquen_two_invoices_min_per_invoice(self):
        """Factura A neto 250.000 (< 300.000) + Factura B neto 350.000 (> 300.000),
        pagadas juntas. Nativo sumaría (600.000 > 300.000 → retiene sobre todo). En
        Neuquén solo se retiene sobre B: base 350.000, 2% = 7.000."""
        inv_a = self._make_vendor_invoice(250000.0, "6-11")
        inv_b = self._make_vendor_invoice(350000.0, "6-12")
        wth = self._withholding_for(inv_a + inv_b, self.tax_iibb_nqn)
        self.assertEqual(wth.base_amount, 350000.0, "Base = solo el neto de la factura que supera el mínimo")
        self.assertEqual(wth.amount, 7000.0, "2% de 350.000 = 7.000 (sin sumar la factura de 250.000)")

    def test_02_neuquen_two_invoices_both_below(self):
        """Dos facturas, ambas por debajo del mínimo (250.000 y 280.000) → no retiene,
        aunque la suma (530.000) supere el mínimo."""
        inv_a = self._make_vendor_invoice(250000.0, "6-21")
        inv_b = self._make_vendor_invoice(280000.0, "6-22")
        wth = self._withholding_for(inv_a + inv_b, self.tax_iibb_nqn)
        self.assertEqual(wth.base_amount, 0.0)
        self.assertEqual(wth.amount, 0.0, "Ninguna factura supera el mínimo → sin retención")

    def test_03_neuquen_two_invoices_both_above(self):
        """Dos facturas, ambas por encima del mínimo (350.000 y 400.000) → retiene sobre
        la suma de ambas: base 750.000, 2% = 15.000."""
        inv_a = self._make_vendor_invoice(350000.0, "6-31")
        inv_b = self._make_vendor_invoice(400000.0, "6-32")
        wth = self._withholding_for(inv_a + inv_b, self.tax_iibb_nqn)
        self.assertEqual(wth.base_amount, 750000.0)
        self.assertEqual(wth.amount, 15000.0)

    # ─── Factura única: se mantiene el comportamiento nativo ───────────────────

    def test_04_neuquen_single_invoice_below(self):
        """Una factura neto 250.000 < 300.000 → no retiene (igual que nativo)."""
        inv = self._make_vendor_invoice(250000.0, "5-4")
        wth = self._withholding_for(inv, self.tax_iibb_nqn)
        self.assertEqual(wth.amount, 0.0)

    def test_05_neuquen_single_invoice_above(self):
        """Una factura neto 350.000 > 300.000 → retiene 2% = 7.000 (igual que nativo)."""
        inv = self._make_vendor_invoice(350000.0, "5-5")
        wth = self._withholding_for(inv, self.tax_iibb_nqn)
        self.assertEqual(wth.base_amount, 350000.0)
        self.assertEqual(wth.amount, 7000.0)
        # El campo ref muestra el cálculo del importe retenido (como ganancias).
        self.assertTrue(wth.ref, "ref debe mostrar el cálculo de la retención")
        self.assertIn("2.0%", wth.ref)

    # ─── Control: sin Neuquén se suman las bases (comportamiento nativo) ───────

    def test_06_non_neuquen_sums_bases(self):
        """Mismas dos facturas (250.000 + 350.000) con jurisdicción distinta de Neuquén:
        el nativo suma las bases (600.000 > 300.000) y retiene sobre el total: 2% = 12.000."""
        inv_a = self._make_vendor_invoice(250000.0, "6-61")
        inv_b = self._make_vendor_invoice(350000.0, "6-62")
        wth = self._withholding_for(inv_a + inv_b, self.tax_iibb_no_nqn)
        self.assertEqual(wth.base_amount, 600000.0)
        self.assertEqual(wth.amount, 12000.0)

    # ─── Pago parcial de una factura que supera el mínimo → prorrateo ──────────

    def test_07_neuquen_partial_payment_qualifying_prorates(self):
        """Pago parcial (50%) de una factura de neto 350.000 (> mínimo). La base baja al
        proporcional (175.000, < mínimo), pero como la factura supera el mínimo se
        retiene prorrateado: 2% de 175.000 = 3.500 (el nativo lo anularía)."""
        inv = self._make_vendor_invoice(350000.0, "6-71")
        wth = self._withholding_for(inv, self.tax_iibb_nqn)
        wth.base_amount = 175000.0  # base proporcional de un pago del 50%
        wth._compute_amount()
        self.assertEqual(wth.amount, 3500.0, "Prorrateo: 2% de 175.000 = 3.500")

    def test_08_non_neuquen_partial_payment_blocks(self):
        """Mismo escenario con jurisdicción distinta de Neuquén: el gate de base nativo
        anula la retención (175.000 <= 300.000) → 0."""
        inv = self._make_vendor_invoice(350000.0, "6-81")
        wth = self._withholding_for(inv, self.tax_iibb_no_nqn)
        wth.base_amount = 175000.0
        wth._compute_amount()
        self.assertEqual(wth.amount, 0.0)
