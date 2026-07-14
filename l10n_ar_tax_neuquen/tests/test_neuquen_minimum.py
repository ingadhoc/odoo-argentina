from odoo import Command
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestNeuquenMinimum(TestArWithholdingArRi):
    """Tests de aceptación para el mínimo sujeto a retención de IIBB Neuquén.

    En Neuquén el mínimo (campo "Minimum Base" / ``l10n_ar_base_minimum_threshold``) se
    evalúa sobre el neto total de la factura (base imponible sin IVA), no sobre la base
    retenida (``base_amount``, que para ``iibb_total`` es el total con impuestos) ni
    sobre el total del pago (Res. Gral. 276/DPR/17, art. 10).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.neuquen = cls.env.ref("base.state_ar_q")
        cls.wth_seq_nqn = cls.env["ir.sequence"].create(
            {"implementation": "standard", "name": "wth neuquen test", "padding": 8, "number_increment": 1}
        )

        # Retención IIBB 2% con mínimo por base = 300.000, jurisdicción Neuquén
        cls.tax_iibb_nqn = cls.tax_wth_test_1.copy(
            default={
                "name": "IIBB Neuquén 2%",
                "amount": 2,
                "l10n_ar_state_id": cls.neuquen.id,
                "l10n_ar_withholding_sequence_id": cls.wth_seq_nqn.id,
                "l10n_ar_non_taxable_amount": 0,
                "l10n_ar_payment_minimum_threshold": 0,
                "l10n_ar_base_minimum_threshold": 300000,
                "l10n_ar_minimum_threshold": 0,
            }
        )

        # Misma configuración pero SIN jurisdicción Neuquén (control)
        cls.tax_iibb_no_nqn = cls.tax_wth_test_1.copy(
            default={
                "name": "IIBB Otra Jurisdicción 2%",
                "amount": 2,
                "l10n_ar_state_id": False,
                "l10n_ar_withholding_sequence_id": cls.wth_seq_nqn.id,
                "l10n_ar_non_taxable_amount": 0,
                "l10n_ar_payment_minimum_threshold": 0,
                "l10n_ar_base_minimum_threshold": 300000,
                "l10n_ar_minimum_threshold": 0,
            }
        )

    def _make_vendor_invoice(self, price_unit, doc_number):
        """Factura de proveedor con IVA 21% y neto = price_unit."""
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

    def _make_withholding_line(self, wth_tax, base_amount, invoice):
        payable_line = invoice.line_ids.filtered(lambda l: l.account_type == "liability_payable")
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": invoice.partner_id.id,
                "amount": invoice.amount_total,
                "date": "2023-01-01",
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        payment.to_pay_move_line_ids = [Command.set(payable_line.ids)]
        wth_line = self.env["l10n_ar.payment.withholding"].create({"payment_id": payment.id, "tax_id": wth_tax.id})
        wth_line.base_amount = base_amount
        wth_line._compute_amount()
        return payment, wth_line

    # ─── Caso del cliente/video: neto < mínimo → no retiene ────────────────────

    def test_01_neuquen_net_below_minimum_blocks(self):
        """Factura neto 259.339,04 + IVA = 313.800,24. La base retenida es el total con
        impuestos (313.800,24 > 300.000, el gate estándar no bloquea), pero el neto de
        la factura (259.339,04) no supera el mínimo → NO corresponde retener."""
        invoice = self._make_vendor_invoice(price_unit=259339.04, doc_number="4-1")
        __, wth = self._make_withholding_line(self.tax_iibb_nqn, base_amount=313800.24, invoice=invoice)
        self.assertEqual(wth.amount, 0.0, "Neto 259.339,04 <= mínimo 300.000 → sin retención")

    # ─── Neuquén: neto > mínimo → retiene ──────────────────────────────────────

    def test_02_neuquen_net_above_minimum_applies(self):
        """Factura neto 350.000 > mínimo 300.000 → retiene 2% sobre la base."""
        invoice = self._make_vendor_invoice(price_unit=350000.0, doc_number="4-2")
        __, wth = self._make_withholding_line(self.tax_iibb_nqn, base_amount=350000.0, invoice=invoice)
        self.assertEqual(wth.amount, 7000.0, "Neto 350.000 > mínimo 300.000 → 2% de 350.000 = 7.000")

    # ─── Control: sin Neuquén se usa la base retenida (gate estándar) ──────────

    def test_03_non_neuquen_uses_base_amount(self):
        """Mismo neto pero jurisdicción distinta de Neuquén: el gate estándar compara
        contra la base retenida (total 313.800,24 > 300.000) → retiene 2% sobre la base.
        Confirma que la comparación contra el neto de factura aplica SOLO a Neuquén."""
        invoice = self._make_vendor_invoice(price_unit=259339.04, doc_number="4-3")
        __, wth = self._make_withholding_line(self.tax_iibb_no_nqn, base_amount=313800.24, invoice=invoice)
        self.assertEqual(wth.amount, 6276.0, "Base 313.800,24 > mínimo 300.000 → 2% = 6.276,00")
