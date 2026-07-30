"""
Tests del monto mínimo de base en percepciones de venta AR
(`l10n_ar_base_minimum_threshold`, ver l10n_ar_tax/models/account_tax.py).

La base se evalúa por documento y por impuesto, en moneda de la compañía: se suman
las bases de las líneas que llevan la percepción (las que no la llevan no suman); si
la suma no supera el umbral, la percepción es 0; si lo supera, se calcula sobre la
base completa.

Casos (alícuota 3%, umbral 300000):
    1. Base 301000 (> umbral) → percepción 9030.
    2. Base 299000 (< umbral) → percepción 0.
    3. Sin umbral configurado (0) → percepción normal aunque la base sea baja.
    4. Dos líneas de 200000 con la percepción + dos líneas sin ella → percepción
       sobre 400000.
    5. Factura en USD con nominal < umbral pero convertido > umbral → percibe.
    6. Factura en USD cuyo valor convertido no llega al umbral → no percibe.
    7. Dos líneas con percepción de 180000 con 5% de descuento y dos líneas sin
       percepción con 10% de descuento → percepción sobre 342000.
"""

from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestPerceptionBaseMinimumThreshold(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Percepción de venta con alícuota fija 3%. Usamos un impuesto propio y no la
        # percepción CABA "aplicada" de demo (que tiene amount=0 y resuelve su alícuota
        # vía padrón) para fijar la alícuota y aislar el gate por base mínima.
        perception_group = cls.env.ref(
            "account.%i_ri_tax_percepcion_iibb_caba_aplicada" % cls.env.company.id
        ).tax_group_id
        cls.perception_tax = cls.env["account.tax"].create(
            {
                "name": "Test Percepción IIBB 3%",
                "amount": 3.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "country_id": cls.env.ref("base.ar").id,
                "company_id": cls.company_ri.id,
                "l10n_ar_state_id": cls.env.ref("base.state_ar_c").id,
                "tax_group_id": perception_group.id,
            }
        )

        # 1 USD = 1000 ARS desde el 01/01/2025 (las facturas de los tests son del 15/01).
        cls.usd = cls.setup_other_currency("USD", rates=[("2025-01-01", 0.001)])

    def _perception_amount(self, lines, currency=None):
        """Crea y confirma una factura de cliente y devuelve la percepción.

        :param lines: lista de tuplas (price_unit, lleva_percepcion[, descuento_%]). La
                      línea siempre lleva IVA 21%; la base de la percepción es el neto.
        :param currency: moneda de la factura (default: la de la compañía).
        :return: monto de percepción, en la moneda de la factura.
        """
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.res_partner_adhoc.id,
                "company_id": self.company_ri.id,
                "currency_id": (currency or self.company_ri.currency_id).id,
                "invoice_date": "2025-01-15",
                "date": "2025-01-15",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.service_iva_21.id,
                            "quantity": 1,
                            "price_unit": price_unit,
                            "discount": discount[0] if discount else 0.0,
                            "tax_ids": [
                                Command.set(
                                    (
                                        self.tax_21
                                        + (self.perception_tax if with_perception else self.env["account.tax"])
                                    ).ids
                                )
                            ],
                        }
                    )
                    for price_unit, with_perception, *discount in lines
                ],
            }
        )
        invoice.action_post()
        perception_lines = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.perception_tax)
        return abs(sum(perception_lines.mapped("amount_currency")))

    def test_01_base_above_threshold(self):
        """Base 301000 > umbral 300000 → percepción sobre la base completa: 9030."""
        self.perception_tax.l10n_ar_base_minimum_threshold = 300000
        self.assertAlmostEqual(self._perception_amount([(301000.0, True)]), 9030.0, places=2)

    def test_02_base_below_threshold(self):
        """Base 299000 < umbral 300000 → percepción 0."""
        self.perception_tax.l10n_ar_base_minimum_threshold = 300000
        self.assertAlmostEqual(self._perception_amount([(299000.0, True)]), 0.0, places=2)

    def test_03_no_threshold_perceives_normally(self):
        """Sin umbral configurado (0), una base baja igual percibe: 1000 * 3% = 30."""
        self.perception_tax.l10n_ar_base_minimum_threshold = 0
        self.assertAlmostEqual(self._perception_amount([(1000.0, True)]), 30.0, places=2)

    def test_04_base_is_aggregated_only_over_lines_with_the_tax(self):
        """Dos líneas de 200000 con la percepción (ninguna supera el umbral por sí sola,
        la suma sí) y dos líneas sin la percepción → percepción sobre 400000 = 12000."""
        self.perception_tax.l10n_ar_base_minimum_threshold = 300000
        amount = self._perception_amount([(200000.0, True), (200000.0, True), (500000.0, False), (500000.0, False)])
        self.assertAlmostEqual(amount, 12000.0, places=2)

    def test_05_foreign_currency_converted_base_above_threshold(self):
        """500 USD = 500000 ARS: el nominal no llega al umbral pero el convertido sí
        (el umbral está en moneda de la compañía) → percibe 500 * 3% = 15 USD."""
        self.perception_tax.l10n_ar_base_minimum_threshold = 300000
        self.assertAlmostEqual(self._perception_amount([(500.0, True)], currency=self.usd), 15.0, places=2)

    def test_06_foreign_currency_converted_base_below_threshold(self):
        """200 USD = 200000 ARS < umbral 300000 ARS → percepción 0."""
        self.perception_tax.l10n_ar_base_minimum_threshold = 300000
        self.assertAlmostEqual(self._perception_amount([(200.0, True)], currency=self.usd), 0.0, places=2)

    def test_07_base_with_discounts(self):
        """Dos líneas con percepción de 180000 con 5% de descuento (171000 cada una) y
        dos líneas sin percepción con 10% de descuento.

        La base del régimen es la neta de descuentos y solo de las líneas que llevan el
        impuesto: 342000 > umbral 300000 → percepción 342000 * 3% = 10260."""
        self.perception_tax.l10n_ar_base_minimum_threshold = 300000
        amount = self._perception_amount(
            [(180000.0, True, 5.0), (180000.0, True, 5.0), (100000.0, False, 10.0), (100000.0, False, 10.0)]
        )
        self.assertAlmostEqual(amount, 10260.0, places=2)
