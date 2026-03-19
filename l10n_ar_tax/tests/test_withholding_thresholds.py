from odoo import Command
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestWithholdingThresholds(TestArWithholdingArRi):
    """
    Acceptance tests for the minimum threshold gates on withholding/perception lines.

    Gates evaluated in _tax_compute_all_helper (non-earnings taxes):
      1. l10n_ar_payment_minimum_threshold – gate por monto de pago
      2. l10n_ar_base_minimum_threshold    – gate por base imponible calculada
      3. l10n_ar_minimum_threshold         – gate final por importe calculado (todos los tipos)

    Ganancias: no aplica gates 1/2; solo gate 3 y deducción de l10n_ar_non_taxable_amount.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.wth_seq_thr = cls.env["ir.sequence"].create(
            {"implementation": "standard", "name": "wth threshold test", "padding": 8, "number_increment": 1}
        )

        # IIBB retención 3% (base sin impuestos) – Cases 1, 2, 3
        cls.tax_iibb_3pct = cls.tax_wth_test_1.copy(
            default={
                "name": "IIBB Threshold Test 3%",
                "amount": 3,
                "l10n_ar_withholding_sequence_id": cls.wth_seq_thr.id,
                "l10n_ar_non_taxable_amount": 0,
                "l10n_ar_payment_minimum_threshold": 0,
                "l10n_ar_base_minimum_threshold": 0,
                "l10n_ar_minimum_threshold": 0,
            }
        )

        # IIBB retención 0.5% – Case 4
        cls.tax_iibb_half_pct = cls.tax_wth_test_1.copy(
            default={
                "name": "IIBB Threshold Test 0.5%",
                "amount": 0.5,
                "l10n_ar_withholding_sequence_id": cls.wth_seq_thr.id,
                "l10n_ar_non_taxable_amount": 0,
                "l10n_ar_payment_minimum_threshold": 0,
                "l10n_ar_base_minimum_threshold": 0,
                "l10n_ar_minimum_threshold": 0,
            }
        )

        # Ganancias 10% con non_taxable_amount=100 – Case 5
        cls.tax_earnings_10pct = cls.tax_wth_earnings_incurred_test_6.copy(
            default={
                "name": "Earnings Threshold Test 10%",
                "amount": 10,
                "amount_type": "percent",
                "l10n_ar_code": "EARN_THR_TEST",
                "l10n_ar_non_taxable_amount": 100.0,
                "l10n_ar_withholding_sequence_id": cls.wth_seq_thr.id,
            }
        )

    # ─── helpers ────────────────────────────────────────────────────────────

    def _make_vendor_invoice(self, price_unit=100.0, doc_number="1-1"):
        """Crea y confirma una factura de proveedor con IVA 21%."""
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
        """
        Crea un pago borrador ligado a la factura (para que to_pay_move_line_ids esté
        seteado y to_pay_amount sea el total de la factura), agrega una línea de
        retención con base_amount manual y dispara _compute_amount.

        Retorna (payment, withholding_line).
        """
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

        # base_amount es store=True, readonly=False → podemos asignarlo directamente.
        wth_line = self.env["l10n_ar.payment.withholding"].create({"payment_id": payment.id, "tax_id": wth_tax.id})
        wth_line.base_amount = base_amount
        wth_line._compute_amount()
        return payment, wth_line

    def _simulate_posted_earnings_base(self, base_amount, tax):
        """
        Crea un asiento contable publicado que simula la línea de base de un pago
        de Ganancias ya confirmado (como si un pago anterior del período tuviera
        ese importe de base en account.move.line).

        Esto es equivalente a haber confirmado un pago anterior con esa retención.
        """
        account_id = self.company_data["default_account_payable"]
        base_entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2023-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": account_id.id,
                            "balance": -base_amount,
                            "partner_id": self.res_partner_adhoc.id,
                            # tax_ids en la línea de base → leído por _get_same_period_base_domain
                            "tax_ids": [Command.set([tax.id])],
                        }
                    ),
                    Command.create(
                        {
                            "account_id": account_id.id,
                            "balance": base_amount,
                            "partner_id": self.res_partner_adhoc.id,
                        }
                    ),
                ],
            }
        )
        base_entry.action_post()
        return base_entry

    # ─── Case 1: IIBB – gate por pago pasa → retiene ────────────────────────

    def test_01_iibb_payment_threshold_applies(self):
        """
        Caso 1: Factura 100+IVA21=121. payment_minimum_threshold=105.
        121 > 105 → pasa el gate → calcula 3% sobre base 100 = 3.
        """
        self.tax_iibb_3pct.l10n_ar_payment_minimum_threshold = 105
        invoice = self._make_vendor_invoice(price_unit=100.0, doc_number="3-1")
        __, wth = self._make_withholding_line(self.tax_iibb_3pct, base_amount=100.0, invoice=invoice)
        self.assertEqual(wth.amount, 3.0)

    # ─── Case 2: IIBB – gate por pago bloquea → no retiene ──────────────────

    def test_02_iibb_payment_threshold_blocks(self):
        """
        Caso 2: Misma factura 121. payment_minimum_threshold=130.
        121 <= 130 → bloqueado → retención = 0.
        """
        self.tax_iibb_3pct.write(
            {
                "l10n_ar_payment_minimum_threshold": 130,
                "l10n_ar_base_minimum_threshold": 0,
                "l10n_ar_minimum_threshold": 0,
            }
        )
        invoice = self._make_vendor_invoice(price_unit=100.0, doc_number="3-2")
        __, wth = self._make_withholding_line(self.tax_iibb_3pct, base_amount=100.0, invoice=invoice)
        self.assertEqual(wth.amount, 0.0)

    # ─── Case 3: IIBB – gate por base bloquea → no retiene ──────────────────

    def test_03_iibb_base_threshold_blocks(self):
        """
        Caso 3: payment_minimum_threshold=0 (pasa), base=100, base_minimum_threshold=105.
        100 <= 105 → bloqueado → retención = 0.
        """
        self.tax_iibb_3pct.write(
            {
                "l10n_ar_payment_minimum_threshold": 0,
                "l10n_ar_base_minimum_threshold": 105,
                "l10n_ar_minimum_threshold": 0,
            }
        )
        invoice = self._make_vendor_invoice(price_unit=100.0, doc_number="3-3")
        __, wth = self._make_withholding_line(self.tax_iibb_3pct, base_amount=100.0, invoice=invoice)
        self.assertEqual(wth.amount, 0.0)

    # ─── Case 4: los 3 gates en cadena, último bloquea ──────────────────────

    def test_04_minimum_amount_threshold_blocks(self):
        """
        Caso 4: payment_minimum_threshold=0, base_minimum_threshold=1 (base=100>1, pasa),
        alícuota 0.5% → tax=0.5, minimum_threshold=10 → 0.5 < 10 → retención = 0.
        """
        self.tax_iibb_half_pct.write(
            {
                "l10n_ar_payment_minimum_threshold": 0,
                "l10n_ar_base_minimum_threshold": 1,
                "l10n_ar_minimum_threshold": 10,
            }
        )
        invoice = self._make_vendor_invoice(price_unit=100.0, doc_number="3-4")
        __, wth = self._make_withholding_line(self.tax_iibb_half_pct, base_amount=100.0, invoice=invoice)
        self.assertEqual(wth.amount, 0.0)

    # ─── Case 5: Ganancias – non_taxable_amount consumible por acumulado ─────

    def test_05_earnings_non_taxable_amount_accumulated(self):
        """
        Caso 5: Ganancias 10%, non_taxable_amount=100.

        Pago1 (base=80, sin acumulado previo):
          net = max(0, 80 + 0 - 100) = 0 → retención = 0.

        Pago2 (base=80, same_period_base=80 del pago anterior ya publicado):
          net = max(0, 80 + 80 - 100) = 60 → 10% de 60 = 6.

        Verifica que la lógica de acumulado de Ganancias no se haya roto.
        """
        self.tax_earnings_10pct.l10n_ar_non_taxable_amount = 100.0

        # Pago1: sin acumulado anterior → net negativo → amount = 0
        invoice1 = self._make_vendor_invoice(price_unit=80.0, doc_number="3-5")
        payment, wth1 = self._make_withholding_line(self.tax_earnings_10pct, base_amount=80.0, invoice=invoice1)
        self.assertEqual(wth1.amount, 0.0, "Pago1: base 80, no imponible 100 → sin retención")
        payment.action_post()

        # Pago2: same_period_base = 80 → net = 80 + 80 - 100 = 60 → 10% = 6
        invoice2 = self._make_vendor_invoice(price_unit=80.0, doc_number="3-6")
        __, wth2 = self._make_withholding_line(self.tax_earnings_10pct, base_amount=80.0, invoice=invoice2)
        self.assertEqual(wth2.amount, 6.0, "Pago2: base acumulada 160 - no imponible 100 = 60 → 10% = 6")
