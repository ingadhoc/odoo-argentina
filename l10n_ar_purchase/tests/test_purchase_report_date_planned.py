from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPurchaseReportDatePlanned(TestArCommon):
    """The request for quotation prints the requested ship date once, in every report layout."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier = cls.env["res.partner"].create(
            {
                "name": "Proveedor Test",
                "is_company": True,
                "supplier_rank": 1,
                "country_id": cls.env.ref("base.ar").id,
                "vat": "30500010912",
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
            }
        )
        cls.product = cls.env["product.product"].create({"name": "Producto Test", "type": "consu"})

    def _make_po(self, **extra):
        vals = {
            "partner_id": self.supplier.id,
            "company_id": self.company_ri.id,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_qty": 1, "price_unit": 100})],
            **extra,
        }
        return self.env["purchase.order"].with_company(self.company_ri).create(vals)

    def _render_quotation(self, po):
        html, _ = self.env["ir.actions.report"]._render_qweb_html("purchase.report_purchasequotation", po.ids)
        return html.decode("utf-8")

    def test_quotation_requested_ship_date_in_every_layout(self):
        # With a shipping address the native report also prints the date in information_block.
        orders = self._make_po() | self._make_po(dest_address_id=self.supplier.id)
        for layout in self.env["report.layout"].search([]):
            self.company_ri.external_report_layout_id = layout.view_id
            for po in orders:
                with self.subTest(layout=layout.name, dest_address=bool(po.dest_address_id)):
                    self.assertTrue(po.date_planned)
                    html = self._render_quotation(po)
                    self.assertEqual(html.count("Requested Ship Date:"), 1)
