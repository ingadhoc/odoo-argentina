"""
Tests para map_tax en posiciones fiscales argentinas (l10n_ar_tax).
Escenarios cubiertos:
    1. Pos. Fiscal sólo percepción con domestic FP con sustitución → IVA 21% no se reemplaza por IVA 0%
    2. Pos. Fiscal con tax_ids explícitos → map_tax aplica la sustitución correctamente (super)
    3. Factura de cliente con Pos. Fiscal con tax_ids explícitos → _get_computed_taxes() aplica IVA 0% reemplazando IVA 21%
    4. Factura de cliente con Pos. Fiscal sólo percepción → _get_computed_taxes() conserva IVA 21% sin sustituirlo
    5. Pago de factura de cliente con Pos. Fiscal sólo percepción → monto del pago refleja IVA 21% (1210), no IVA 0% (1000)
"""

from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestMapTaxFiscalPosition(TestArCommon):
    """Tests de map_tax para posiciones fiscales de percepción/retención."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Impuesto de percepción IIBB CABA para usar en l10n_ar_tax_ids
        cls.caba_perception_tax = cls.env.ref("account.%i_ri_tax_percepcion_iibb_caba_aplicada" % cls.env.company.id)

        # Posición fiscal "percepción-only": sin tax_ids, con l10n_ar_tax_ids
        cls.perception_only_fp = cls.env["account.fiscal.position"].create(
            {
                "name": "Test FP Percepcion Only",
                "company_id": cls.company_ri.id,
            }
        )
        cls.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": cls.perception_only_fp.id,
                "default_tax_id": cls.caba_perception_tax.id,
                "tax_type": "perception",
            }
        )

        # Posición fiscal con tax_ids explícitos: IVA 21% → IVA 0%
        # En Odoo 19, tax_ids es Many2many a account.tax y el mapeo funciona
        # mediante original_tax_ids en el impuesto destino.
        cls.tax_0.original_tax_ids = [Command.set(cls.tax_21.ids)]
        cls.fp_with_tax_mapping = cls.env["account.fiscal.position"].create(
            {
                "name": "Test FP Con Mapping IVA",
                "company_id": cls.company_ri.id,
                "tax_ids": [Command.set(cls.tax_0.ids)],
            }
        )

    def test_map_tax_perception_only_not_affected_by_domestic_fp_substitution(self):
        """
        Incluso si el domestic FP tiene una sustitución IVA 21% → IVA 0%,
        la FP con sólo percepción debe devolver IVA 21% sin cambios.
        """
        # Configurar domestic FP con sustitución IVA 21% → IVA 0%
        domestic_fp = self.company_ri.domestic_fiscal_position_id
        if not domestic_fp:
            self.skipTest("No se encontró domestic fiscal position para la compañía de test.")

        # Agregar sustitución al domestic FP via original_tax_ids en IVA 0%
        if self.tax_21 not in self.tax_0.original_tax_ids:
            self.tax_0.original_tax_ids = [Command.link(self.tax_21.id)]
        if self.tax_0 not in domestic_fp.tax_ids:
            domestic_fp.tax_ids = [Command.link(self.tax_0.id)]

        taxes = self.tax_21
        result = self.perception_only_fp.map_tax(taxes)
        self.assertEqual(
            result,
            self.tax_21,
            "La FP percepcion-only no debe aplicar la sustitucion IVA 21%→IVA 0% del domestic FP.",
        )

    def test_map_tax_fp_with_explicit_tax_ids_applies_substitution(self):
        """
        Una FP con tax_ids explícitos debe aplicar la sustitución mediante super().map_tax().
        """
        taxes = self.tax_21
        result = self.fp_with_tax_mapping.map_tax(taxes)
        self.assertEqual(
            result,
            self.tax_0,
            "Una FP con tax_ids explícitos debe aplicar la sustitucion de impuestos.",
        )

    def test_invoice_with_fp_tax_mapping_applies_vat_substitution(self):
        """
        Al crear una factura con una FP que tiene tax_ids explícitos (IVA 21% → IVA 0%),
        sin tax_ids en la línea, _compute_tax_ids → _get_computed_taxes() → map_tax()
        debe sustituir IVA 21% por IVA 0%.
        Valida que el flujo de impuestos en facturas de cliente aplica correctamente la sustitución
        definida en la FP con tax_ids explícitos."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.res_partner_adhoc.id,
                "fiscal_position_id": self.fp_with_tax_mapping.id,
                "company_id": self.company_ri.id,
                "invoice_date": "2025-01-15",
                "date": "2025-01-15",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.service_iva_21.id,
                            "quantity": 1,
                            "price_unit": 1000.0,
                        }
                    )
                ],
                "l10n_latam_document_number": "0001-00000002",
            }
        )
        invoice.action_post()

        line_taxes = invoice.invoice_line_ids.tax_ids
        self.assertIn(
            self.tax_0,
            line_taxes,
            "IVA 0% debe estar en la línea: la FP con tax_ids debe sustituir IVA 21% por IVA 0%.",
        )
        self.assertNotIn(
            self.tax_21,
            line_taxes,
            "IVA 21% debe haber sido reemplazado por IVA 0% via la FP con mapping explícito.",
        )

    def test_invoice_with_perception_only_fp_preserves_vat_taxes(self):
        """
        Al crear una factura con una FP con sólo percepción sin tax_ids explícitos en la línea,
        Odoo computa tax_ids vía _compute_tax_ids → _get_computed_taxes() → map_tax().
        El IVA 21% del producto debe conservarse sin ser reemplazado por IVA 0%.
        """
        domestic_fp = self.company_ri.domestic_fiscal_position_id
        if not domestic_fp:
            self.skipTest("No se encontró domestic fiscal position para la compañía de test.")

        # Asegurar que el domestic FP tiene sustitución IVA 21% → IVA 0%
        if self.tax_21 not in self.tax_0.original_tax_ids:
            self.tax_0.original_tax_ids = [Command.link(self.tax_21.id)]
        if self.tax_0 not in domestic_fp.tax_ids:
            domestic_fp.tax_ids = [Command.link(self.tax_0.id)]

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.res_partner_adhoc.id,
                "fiscal_position_id": self.perception_only_fp.id,
                "company_id": self.company_ri.id,
                "invoice_date": "2025-01-15",
                "date": "2025-01-15",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.service_iva_21.id,
                            "quantity": 1,
                            "price_unit": 1000.0,
                        }
                    )
                ],
                "l10n_latam_document_number": "0001-00000001",
            }
        )
        invoice.action_post()

        line_taxes = invoice.invoice_line_ids.tax_ids
        self.assertIn(
            self.tax_21,
            line_taxes,
            "IVA 21% debe estar presente en la línea cuando se usa una FP percepcion-only.",
        )
        self.assertNotIn(
            self.tax_0,
            line_taxes,
            "IVA 0% no debe aparecer en la línea; la FP percepcion-only no debe sustituir impuestos.",
        )

    def test_payment_for_invoice_with_perception_only_fp_uses_correct_tax_amount(self):
        """
        Al registrar el pago de una factura de cliente con FP percepción-only,
        el monto del pago debe reflejar IVA 21% (base 1000 → total 1210), no IVA 0% (1000).
        Si map_tax() hubiera aplicado la sustitución del domestic FP, el total de la
        factura sería 1000 y el pago por 1210 dejaría un residual, o el pago se
        registraría por 1000 y el total sería incorrecto.
        """
        domestic_fp = self.company_ri.domestic_fiscal_position_id
        if not domestic_fp:
            self.skipTest("No se encontró domestic fiscal position para la compañía de test.")

        # Asegurar sustitución activa en domestic FP para que el escenario sea realista
        if self.tax_21 not in self.tax_0.original_tax_ids:
            self.tax_0.original_tax_ids = [Command.link(self.tax_21.id)]
        if self.tax_0 not in domestic_fp.tax_ids:
            domestic_fp.tax_ids = [Command.link(self.tax_0.id)]

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.res_partner_adhoc.id,
                "fiscal_position_id": self.perception_only_fp.id,
                "company_id": self.company_ri.id,
                "invoice_date": "2025-01-15",
                "date": "2025-01-15",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.service_iva_21.id,
                            "quantity": 1,
                            "price_unit": 1000.0,
                        }
                    )
                ],
                "l10n_latam_document_number": "0001-00000003",
            }
        )
        invoice.action_post()

        self.assertAlmostEqual(
            invoice.amount_total,
            1210.0,
            places=2,
            msg="El total de la factura debe incluir IVA 21% (1000 + 210 = 1210).",
        )

        (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"payment_date": "2025-01-15"})
            .action_create_payments()
        )

        self.assertAlmostEqual(
            invoice.amount_residual,
            0.0,
            places=2,
            msg="La factura debe quedar completamente saldada con el monto IVA 21% (1210).",
        )
