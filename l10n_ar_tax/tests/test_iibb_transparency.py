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

        # Copiamos la percepción de IIBB demo (tributo ARCA 07) ajustando nombre
        # único, etiqueta (invoice_label), alícuota y jurisdicción.
        def _perc(name, invoice_label, amount, state_xmlid):
            return cls.tax_perc_iibb.copy(
                {
                    "name": name,
                    "invoice_label": invoice_label,
                    "amount": amount,
                    "l10n_ar_state_id": cls.env.ref(state_xmlid).id,
                }
            )

        cls.perc_caba = _perc("PERC CABA (test)", "ALÍCUOTA ISIB CABA", 3.0, "base.state_ar_c")
        cls.perc_tuc = _perc("PERC TUC (test)", "Perc IIBB Tucumán", 3.0, "base.state_ar_t")
        cls.perc_er = _perc(
            "PERC ER (test)", "Imp. Pciales o IIBB o Profesiones Liberales Entre Ríos", 3.5, "base.state_ar_e"
        )
        cls.perc_chubut = _perc("PERC CHT (test)", "VALOR APROXIMADO DEL ISIB CHUBUT", 2.0, "base.state_ar_u")

    def _invoice_b_con_percepciones(self):
        def line(name, tax):
            return self._prepare_invoice_line(
                product_id=self.service_iva_21, price_unit=1000.0, name=name, tax_ids=self.tax_21 + tax
            )

        return self._create_invoice_ar(
            partner_id=self.partner_cf,
            company_id=self.company_ri,
            invoice_date="2026-06-20",
            invoice_line_ids=[
                line("CABA", self.perc_caba),
                line("TUC", self.perc_tuc),
                line("ER", self.perc_er),
                line("CHT", self.perc_chubut),
            ],
        )

    def test_iibb_transparency_legends(self):
        """Leyenda = etiqueta del impuesto + alícuota; ER y Chubut van sin alícuota."""
        invoice = self._invoice_b_con_percepciones()
        names = [r["name"] for r in invoice._l10n_ar_get_invoice_custom_tax_summary_for_report()]

        # Se reusa el cuadro nacional: el IVA contenido sigue presente.
        self.assertTrue(any(n.startswith("VAT Content") for n in names), names)
        # Regla general: etiqueta + alícuota.
        self.assertIn("ALÍCUOTA ISIB CABA 3%", names)
        self.assertIn("Perc IIBB Tucumán 3%", names)
        self.assertIn("Imp. Pciales o IIBB o Profesiones Liberales Entre Ríos 3.5%", names)
        # Chubut: solo la etiqueta, sin alícuota.
        self.assertIn("VALOR APROXIMADO DEL ISIB CHUBUT", names)

    def test_iibb_perceptions_excluded_from_totals_box(self):
        """Las percepciones de IIBB no deben aparecer en el cuadro de totales
        (ya están en el de Transparencia Fiscal), y el total no debe cambiar."""
        invoice = self._invoice_b_con_percepciones()
        totals = invoice._l10n_ar_get_invoice_totals_for_report()
        group_ids = {tg["id"] for st in totals["subtotals"] for tg in st["tax_groups"]}

        self.assertNotIn(self.perc_caba.tax_group_id.id, group_ids)
        self.assertAlmostEqual(totals["total_amount_currency"], invoice.amount_total, places=2)

    def test_iibb_transparency_only_on_invoice_b(self):
        """El cuadro de percepciones solo aplica a Facturas B (códigos 6/7/8)."""
        invoice = self._create_invoice_ar(
            partner_id=self.partner,  # RI -> Factura A
            company_id=self.company_ri,
            invoice_date="2026-06-20",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.service_iva_21, price_unit=1000.0, name="CABA", tax_ids=self.tax_21 + self.perc_caba
                ),
            ],
        )
        self.assertNotEqual(invoice.l10n_latam_document_type_id.code, "6")
        names = [r["name"] for r in invoice._l10n_ar_get_invoice_custom_tax_summary_for_report()]
        self.assertFalse(any("ISIB CABA" in n for n in names), names)
