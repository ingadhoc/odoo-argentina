from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPurchaseReportIncoterm(TestArCommon):
    """Verifica que el Incoterm aparezca una sola vez en los reportes de compra
    argentinos y que la ubicación del incoterm no sea mostrada.

    Casos cubiertos (ref. tarea #68236):
    1. Solicitud de Compra con Incoterm → aparece una vez, sin ubicación
    2. Pedido de Compra con Incoterm → aparece una vez, sin ubicación
    3. Sin Incoterm → el campo no aparece en ninguno de los dos reportes
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.incoterm = cls.env["account.incoterms"].create(
            {
                "name": "Free On Board",
                "code": "FOB",
            }
        )

        cls.supplier = cls.env["res.partner"].create(
            {
                "name": "Proveedor Test",
                "is_company": True,
                "supplier_rank": 1,
                "country_id": cls.env.ref("base.ar").id,
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_cuit").id,
                "vat": "30500010912",
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
            }
        )

        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto Test",
                "type": "consu",
            }
        )

    def _make_po(self, incoterm=None, incoterm_location=None, confirm=False):
        vals = {
            "partner_id": self.supplier.id,
            "company_id": self.company_ri.id,
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product.id,
                        "product_qty": 1,
                        "price_unit": 100,
                    },
                )
            ],
        }
        if incoterm:
            vals["incoterm_id"] = incoterm.id
        if incoterm_location:
            vals["incoterm_location"] = incoterm_location
        po = self.env["purchase.order"].with_company(self.company_ri).create(vals)
        if confirm:
            po.button_confirm()
        return po

    def _render_html(self, report_name, po):
        html, _ = self.env["ir.actions.report"]._render_qweb_html(report_name, po.ids)
        return html.decode("utf-8")

    # ------------------------------------------------------------------
    # Caso 1: Solicitud de Compra con Incoterm
    # ------------------------------------------------------------------

    def test_quotation_incoterm_appears_once(self):
        """Solicitud de Compra con Incoterm: aparece exactamente una vez."""
        po = self._make_po(incoterm=self.incoterm)
        html = self._render_html("purchase.report_purchasequotation", po)
        count = html.count("Incoterm:")
        self.assertEqual(count, 1, f"Se esperaba 'Incoterm:' exactamente 1 vez, se encontró {count}")

    def test_quotation_incoterm_location_not_shown(self):
        """Solicitud de Compra: la ubicación del incoterm NO se muestra."""
        po = self._make_po(incoterm=self.incoterm, incoterm_location="Puerto Buenos Aires")
        html = self._render_html("purchase.report_purchasequotation", po)
        self.assertNotIn(
            "Puerto Buenos Aires",
            html,
            "La ubicación del incoterm no debe aparecer en la solicitud de compra",
        )

    # ------------------------------------------------------------------
    # Caso 2: Pedido de Compra con Incoterm
    # ------------------------------------------------------------------

    def test_order_incoterm_appears_once(self):
        """Pedido de Compra con Incoterm: aparece exactamente una vez."""
        po = self._make_po(incoterm=self.incoterm, confirm=True)
        html = self._render_html("purchase.report_purchaseorder", po)
        count = html.count("Incoterm:")
        self.assertEqual(count, 1, f"Se esperaba 'Incoterm:' exactamente 1 vez, se encontró {count}")

    def test_order_incoterm_location_not_shown(self):
        """Pedido de Compra: la ubicación del incoterm NO se muestra."""
        po = self._make_po(incoterm=self.incoterm, incoterm_location="Puerto Buenos Aires", confirm=True)
        html = self._render_html("purchase.report_purchaseorder", po)
        self.assertNotIn(
            "Puerto Buenos Aires",
            html,
            "La ubicación del incoterm no debe aparecer en el pedido de compra",
        )

    # ------------------------------------------------------------------
    # Caso 3: Sin Incoterm
    # ------------------------------------------------------------------

    def test_quotation_without_incoterm(self):
        """Solicitud de Compra sin Incoterm: la etiqueta no aparece."""
        po = self._make_po()
        html = self._render_html("purchase.report_purchasequotation", po)
        self.assertNotIn("Incoterm:", html)

    def test_order_without_incoterm(self):
        """Pedido de Compra sin Incoterm: la etiqueta no aparece."""
        po = self._make_po(confirm=True)
        html = self._render_html("purchase.report_purchaseorder", po)
        self.assertNotIn("Incoterm:", html)
