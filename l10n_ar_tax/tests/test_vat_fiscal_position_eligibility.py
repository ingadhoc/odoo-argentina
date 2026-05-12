"""
Tests de elegibilidad del IVA en el dropdown de impuestos bajo Posición Fiscal
de percepción.

Spec: oba-specs/specs/10_draft/loc-argentina/vat-fiscal-position-deteccion.md
Task: #67409

Matriz 3 × 2 (3 escenarios de factura × 2 estados de `IVA.fiscal_position_ids`):

    | # | PF en factura       | IVA.fiscal_position_ids | Debe ser elegible |
    |---|---------------------|-------------------------|-------------------|
    | 1 | (sin PF)            | [AR Domestic]           | sí                |
    | 2 | (sin PF)            | []                      | sí                |
    | 3 | AR Domestic         | [AR Domestic]           | sí                |
    | 4 | AR Domestic         | []                      | sí                |
    | 5 | Percepciones (test) | [AR Domestic]           | sí (caso fixeado) |
    | 6 | Percepciones (test) | []                      | sí                |

El caso 5 es el que el override de `l10n_ar_tax.account_tax.name_search` arregla.

Cada test simula el call exacto que hace el widget `many2many_tax_tags` al
abrir el dropdown de `tax_ids` en una línea de factura: `web_name_search`
con el `domain` y `context` que declara `account/views/account_move_views.xml`
(líneas 1217-1225). Sin esa fidelidad el test no captura la lógica real del
caso 5 (descubierto raíz por @jgo, sesión 2026-05-13).
"""

from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestVatFiscalPositionEligibility(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.domestic_fp = cls.company_ri.domestic_fiscal_position_id
        if not cls.domestic_fp:
            cls.skipTest_reason = "No se encontró domestic fiscal position para la compañía de test."
            return
        else:
            cls.skipTest_reason = None

        # PF AR-country no doméstica: solo percepciones (sin tax_ids).
        # sequence=999 evita que perception_fp gane el sort de
        # _compute_domestic_fiscal_position_id frente a AR Domestic (sequence=10)
        # y se convierta en la doméstica computada — eso enmascararía el caso 5
        # del bug (el if `fp != domestic_fiscal_position_id` no entraría).
        cls.perception_fp = cls.env["account.fiscal.position"].create(
            {
                "name": "Test FP Percepciones (eligibility)",
                "company_id": cls.company_ri.id,
                "country_id": cls.env.ref("base.ar").id,
                "sequence": 999,
            }
        )
        cls.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": cls.perception_fp.id,
                "default_tax_id": cls.tax_perc_iibb.id,
                "tax_type": "perception",
            }
        )
        cls.company_ri.invalidate_recordset(["domestic_fiscal_position_id"])
        if cls.company_ri.domestic_fiscal_position_id != cls.domestic_fp:
            cls.skipTest_reason = (
                f"Setup inválido: domestic_fiscal_position_id quedó como "
                f"{cls.company_ri.domestic_fiscal_position_id.name} "
                f"en lugar de {cls.domestic_fp.name}."
            )

    def _open_dropdown(self, invoice_fp=None):
        """Simula el call que hace el widget `many2many_tax_tags` al abrir el
        dropdown de impuestos en una línea de factura.

        El view de `account.move.line` (`account/views/account_move_views.xml:1217`)
        declara para el field `tax_ids`:

            domain="[('type_tax_use', '=?', parent.invoice_filter_type_domain),
                     ('company_id', 'parent_of', parent.company_id),
                     ('country_id', '=', parent.tax_country_id)]"
            context="{
                'append_fields': not parent.invoice_filter_type_domain and ['type_tax_use'],
                'active_test': True,
                'dynamic_fiscal_position_id': parent.fiscal_position_id,
            }"

        El widget invoca `web_name_search(name, specification, domain, ...)` con
        ese domain y un with_context() con ese context. Esta función replica
        ese call para una factura con la PF indicada.
        """
        invoice = (
            self.env["account.move"]
            .with_company(self.company_ri)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.res_partner_adhoc.id,
                    "fiscal_position_id": invoice_fp.id if invoice_fp else False,
                }
            )
        )
        view_domain = [
            ("type_tax_use", "=?", invoice.invoice_filter_type_domain),
            ("company_id", "parent_of", invoice.company_id.id),
            ("country_id", "=", invoice.tax_country_id.id),
        ]
        view_context = {
            "append_fields": False,
            "active_test": True,
            "dynamic_fiscal_position_id": invoice.fiscal_position_id.id,
            # hide_original_tax_ids=True lo agrega el widget many2many_tax_tags
            # cuando se abre el dropdown — sin esto, el test pasaba "por suerte"
            # (no capturaba la regresión observada por @jgo el 14/05 en runbot).
            "hide_original_tax_ids": True,
        }
        results = (
            self.env["account.tax"]
            .with_context(**view_context)
            .web_name_search(
                name="",
                specification={"display_name": {}},
                domain=view_domain,
                operator="ilike",
                limit=200,
            )
        )
        return [r["id"] for r in results]

    # ---------- Casos 1-2: sin PF en factura ----------

    def test_01_no_fp_iva_with_domestic(self):
        if self.skipTest_reason:
            self.skipTest(self.skipTest_reason)
        if self.domestic_fp not in self.tax_21.fiscal_position_ids:
            self.tax_21.fiscal_position_ids = [Command.link(self.domestic_fp.id)]
        self.assertIn(
            self.tax_21.id,
            self._open_dropdown(invoice_fp=None),
            "Sin PF activa, IVA 21% con domestic en fiscal_position_ids debe ser elegible.",
        )

    def test_02_no_fp_iva_without_fiscal_position_ids(self):
        if self.skipTest_reason:
            self.skipTest(self.skipTest_reason)
        self.tax_21.fiscal_position_ids = [Command.clear()]
        self.assertIn(
            self.tax_21.id,
            self._open_dropdown(invoice_fp=None),
            "Sin PF activa, IVA 21% sin fiscal_position_ids debe ser elegible.",
        )

    # ---------- Casos 3-4: PF Domestic en factura ----------

    def test_03_domestic_fp_iva_with_domestic(self):
        if self.skipTest_reason:
            self.skipTest(self.skipTest_reason)
        if self.domestic_fp not in self.tax_21.fiscal_position_ids:
            self.tax_21.fiscal_position_ids = [Command.link(self.domestic_fp.id)]
        self.assertIn(
            self.tax_21.id,
            self._open_dropdown(invoice_fp=self.domestic_fp),
            "Con PF Domestic activa, IVA 21% con domestic en fiscal_position_ids debe ser elegible.",
        )

    def test_04_domestic_fp_iva_without_fiscal_position_ids(self):
        if self.skipTest_reason:
            self.skipTest(self.skipTest_reason)
        self.tax_21.fiscal_position_ids = [Command.clear()]
        self.assertIn(
            self.tax_21.id,
            self._open_dropdown(invoice_fp=self.domestic_fp),
            "Con PF Domestic activa, IVA 21% sin fiscal_position_ids debe ser elegible.",
        )

    # ---------- Casos 5-6: PF de percepción en factura ----------

    def test_05_perception_fp_iva_with_domestic(self):
        """Caso del bug original (reportado por @jgo en task #67409, video):
        con PF de percepción activa en la factura y el IVA 21% teniendo a la
        PF Domestic en `fiscal_position_ids`, el IVA debe seguir siendo
        elegible en el dropdown.
        """
        if self.skipTest_reason:
            self.skipTest(self.skipTest_reason)
        if self.domestic_fp not in self.tax_21.fiscal_position_ids:
            self.tax_21.fiscal_position_ids = [Command.link(self.domestic_fp.id)]
        self.assertIn(
            self.tax_21.id,
            self._open_dropdown(invoice_fp=self.perception_fp),
            "Con PF de percepción activa, IVA 21% con domestic en fiscal_position_ids "
            "debe ser elegible (la percepción complementa la doméstica, no la reemplaza).",
        )

    def test_06_perception_fp_iva_without_fiscal_position_ids(self):
        if self.skipTest_reason:
            self.skipTest(self.skipTest_reason)
        self.tax_21.fiscal_position_ids = [Command.clear()]
        self.assertIn(
            self.tax_21.id,
            self._open_dropdown(invoice_fp=self.perception_fp),
            "Con PF de percepción activa, IVA 21% sin fiscal_position_ids debe ser elegible.",
        )

    # ---------- Caso 7: PF de replacement (NO debe activar el override) ----------

    def test_07_replacement_fp_iva_domestic_not_eligible(self):
        """Una PF AR de replacement puro — `tax_ids` con mapeo IVA 21% → 10.5%,
        sin `l10n_ar_tax_ids` — NO debe activar la extensión `is_domestic=True`
        del override. Es decir, bajo esa PF el dropdown debe mostrar SOLO el tax
        target del mapeo (IVA 10.5%), NO el original reemplazado (IVA 21%).

        Caso de uso real (jjs): clientes con PF que cambia IVA 21% → IVA 10.5%
        — la PF se asocia en los impuestos y al estar activa debe restringir,
        no expandir.
        """
        if self.skipTest_reason:
            self.skipTest(self.skipTest_reason)
        # Setup mapeo: tax_0 reemplaza a tax_21 cuando la PF replacement está activa.
        if self.tax_21 not in self.tax_0.original_tax_ids:
            self.tax_0.original_tax_ids = [Command.link(self.tax_21.id)]
        replacement_fp = self.env["account.fiscal.position"].create(
            {
                "name": "Test FP Replacement (IVA 21% → 10.5%)",
                "company_id": self.company_ri.id,
                "country_id": self.env.ref("base.ar").id,
                "sequence": 998,
                "tax_ids": [Command.set(self.tax_0.ids)],
            }
        )
        # Sanity: la PF NO tiene l10n_ar_tax_ids → mi override NO debe entrar.
        self.assertFalse(
            replacement_fp.l10n_ar_tax_ids,
            "Setup inválido: la PF de replacement no debe tener l10n_ar_tax_ids.",
        )
        # IVA 21% con domestic en fiscal_position_ids (estándar v19).
        if self.domestic_fp not in self.tax_21.fiscal_position_ids:
            self.tax_21.fiscal_position_ids = [Command.link(self.domestic_fp.id)]

        eligible = self._open_dropdown(invoice_fp=replacement_fp)
        self.assertNotIn(
            self.tax_21.id,
            eligible,
            "Con PF de replacement activa, IVA 21% (que es el original reemplazado) "
            "NO debe aparecer en el dropdown — solo el target del mapeo.",
        )
