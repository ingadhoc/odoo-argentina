from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestIibbTransparency(TestArCommon):
    """Régimen de Transparencia Fiscal (Ley 27.743): percepciones de IIBB en el
    cuadro del reporte de factura, discriminadas por jurisdicción."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls._create_journal("preprinted")

        # Reusamos el grupo de impuesto de la percepción de IIBB demo (tributo
        # ARCA 07). Copiamos esa percepción y le ajustamos etiqueta, alícuota y
        # jurisdicción para no depender de la alícuota 0 que trae la demo.
        def _perc(label, amount, state_xmlid):
            return cls.tax_perc_iibb.copy(
                {
                    "name": label,
                    "invoice_label": label,
                    "amount": amount,
                    "l10n_ar_state_id": cls.env.ref(state_xmlid).id,
                }
            )

        # Entre Ríos (code E): regla general -> usa la etiqueta del impuesto.
        cls.perc_er = _perc("Percepción IIBB Entre Ríos (test transp)", 3.5, "base.state_ar_e")
        # CABA (code C): leyenda hardcodeada por norma (ignora la etiqueta).
        cls.perc_caba = _perc("Etiqueta CABA que se ignora (test transp)", 3.0, "base.state_ar_c")
        # Chubut (code U): leyenda hardcodeada, sin alícuota.
        cls.perc_chubut = _perc("Etiqueta Chubut que se ignora (test transp)", 2.0, "base.state_ar_u")

    def test_iibb_transparency_legends(self):
        invoice = self._create_invoice_ar(
            partner_id=self.partner_cf,
            company_id=self.company_ri,
            invoice_date="2026-06-20",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.service_iva_21, price_unit=1000.0, name="ER", tax_ids=self.tax_21 + self.perc_er
                ),
                self._prepare_invoice_line(
                    product_id=self.service_iva_21, price_unit=1000.0, name="CABA", tax_ids=self.tax_21 + self.perc_caba
                ),
                self._prepare_invoice_line(
                    product_id=self.service_iva_21,
                    price_unit=1000.0,
                    name="Chubut",
                    tax_ids=self.tax_21 + self.perc_chubut,
                ),
            ],
        )
        results = invoice._l10n_ar_get_invoice_custom_tax_summary_for_report()
        names = [r["name"] for r in results]

        # Se reusa el cuadro nacional: el IVA contenido sigue presente.
        self.assertTrue(
            any(n.startswith("VAT Content") for n in names),
            "Falta la línea de IVA Contenido (régimen nacional reusado): %s" % names,
        )

        # Regla general (Entre Ríos): etiqueta del impuesto + alícuota.
        self.assertTrue(
            any(n.startswith("Percepción IIBB Entre Ríos") and n.endswith("%") for n in names),
            "ER debería usar la etiqueta + alícuota: %s" % names,
        )

        # CABA: leyenda hardcodeada (ignora la etiqueta) + alícuota.
        self.assertTrue(
            any(n.startswith("ALÍCUOTA ISIB CABA") and n.endswith("%") for n in names),
            "CABA debería mostrar la leyenda normada + alícuota: %s" % names,
        )

        # Chubut: leyenda hardcodeada, SIN alícuota.
        self.assertIn("VALOR APROXIMADO DEL ISIB CHUBUT", names)
        self.assertFalse(
            any(n.startswith("VALOR APROXIMADO DEL ISIB CHUBUT") and n.endswith("%") for n in names),
            "Chubut no debe mostrar alícuota: %s" % names,
        )

    def test_iibb_transparency_only_on_invoice_b(self):
        """El cuadro de percepciones solo aplica a Facturas B (códigos 6/7/8)."""
        invoice = self._create_invoice_ar(
            partner_id=self.partner,  # RI -> Factura A
            company_id=self.company_ri,
            invoice_date="2026-06-20",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.service_iva_21, price_unit=1000.0, name="ER", tax_ids=self.tax_21 + self.perc_er
                ),
            ],
        )
        self.assertNotEqual(invoice.l10n_latam_document_type_id.code, "6")
        names = [r["name"] for r in invoice._l10n_ar_get_invoice_custom_tax_summary_for_report()]
        self.assertFalse(
            any("Entre Ríos" in n for n in names), "En Factura A no debería listarse la percepción de IIBB: %s" % names
        )
