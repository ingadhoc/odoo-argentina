"""Santa Fe IIBB withholding base from the PARP contributor type ('C' total, 'D' net)."""

import ast
import base64
import io
import shutil
import zipfile
from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.api import Environment
from odoo.fields import Date
from odoo.tests import tagged
from odoo.tools import file_path

PARP_EXAMPLE_FILE = "l10n_ar_tax/doc/padron_santa_fe/PARP_999999_ejemplo_padron_santa_fe.txt"
CUIT_MULTILATERAL = "20188192514"  # 'C', withholding 0.60
CUIT_LOCAL = "20203032723"  # 'D', withholding 0.80
CUIT_NOT_IN_PADRON = "30111111118"
PADRON_FROM, PADRON_TO = "2026-03-01", "2026-03-31"
PAYMENT_DATE = Date.to_date("2026-03-15")


@tagged("-at_install", "post_install")
class TestPadronSantaFeContributorType(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.santa_fe = cls.env.ref("base.state_ar_s")

        # net-base Santa Fe withholding, as configured today
        tax_group = cls.env["account.tax.group"].create(
            {
                "name": "Test Ret. IIBB Santa Fe",
                "company_id": cls.company_ri.id,
            }
        )
        cls.wth_tax_untaxed = cls.env["account.tax"].create(
            {
                "name": "Ret. IIBB Santa Fe Aplicada 0.6%",
                "amount": 0.6,
                "amount_type": "percent",
                "type_tax_use": "none",
                "country_id": cls.env.ref("base.ar").id,
                "company_id": cls.company_ri.id,
                "l10n_ar_withholding_payment_type": "supplier",
                "l10n_ar_tax_type": "iibb_untaxed",
                "l10n_ar_state_id": cls.santa_fe.id,
                "tax_group_id": tax_group.id,
            }
        )
        fiscal_position = cls.env["account.fiscal.position"].create(
            {
                "name": "Test Padrón Santa Fe",
                "company_id": cls.company_ri.id,
                "l10n_ar_tax_ids": [
                    Command.create(
                        {
                            "default_tax_id": cls.wth_tax_untaxed.id,
                            "tax_type": "withholding",
                            "webservice": "padron",
                        }
                    )
                ],
            }
        )
        cls.wth_line = fiscal_position.l10n_ar_tax_ids

    def _create_example_padron(self):
        """Load the example padron (Santa Fe only accepts ZIP files)."""
        with open(file_path(PARP_EXAMPLE_FILE), encoding="latin-1") as fp:
            content = fp.read()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("PARP.TXT", content)
        padron = self.env["res.company.jurisdiction.padron"].create(
            {
                "company_id": self.company_ri.id,
                "state_id": self.santa_fe.id,
                "file_padron": base64.b64encode(buffer.getvalue()).decode(),
                "filename": "parp_santa_fe.zip",
                "l10n_ar_padron_from_date": PADRON_FROM,
                "l10n_ar_padron_to_date": PADRON_TO,
            }
        )
        self.addCleanup(shutil.rmtree, padron._get_parp_tmp_dir(), ignore_errors=True)
        return padron

    def _create_partner(self, vat):
        return self.env["res.partner"].create(
            {
                "name": "partner_%s" % vat,
                "l10n_latam_identification_type_id": self.env.ref("l10n_ar.it_cuit").id,
                "vat": vat,
            }
        )

    @contextmanager
    def _without_demo_user(self):
        """Skip the demo-data shortcuts of the native tax resolution."""
        real_ref = Environment.ref

        def _ref(env, xml_id, raise_if_not_found=True):
            if xml_id == "base.user_demo":
                return None
            return real_ref(env, xml_id, raise_if_not_found=raise_if_not_found)

        with patch.object(Environment, "ref", _ref):
            yield

    def test_parp_reads_the_contributor_type(self):
        padron = self._create_example_padron()

        self.assertEqual(padron._get_parp_contributor_type(CUIT_MULTILATERAL), "C")
        self.assertEqual(padron._get_parp_contributor_type(CUIT_LOCAL), "D")
        self.assertFalse(padron._get_parp_contributor_type(CUIT_NOT_IN_PADRON))

    def test_parp_tax_type_mapping(self):
        self.assertEqual(self.wth_line._get_parp_tax_type("C"), "iibb_total")
        self.assertFalse(self.wth_line._get_parp_tax_type("D"))
        self.wth_line.tax_type = "perception"
        self.assertFalse(self.wth_line._get_parp_tax_type("C"))

    def test_ensure_tax_creates_and_reuses_the_cm_variant(self):
        tax = self.wth_line._ensure_tax(0.6, l10n_ar_tax_type="iibb_total")

        self.assertNotEqual(tax, self.wth_tax_untaxed)
        self.assertEqual((tax.amount, tax.l10n_ar_tax_type), (0.6, "iibb_total"))
        self.assertIn("CM", tax.name, "el nombre debe distinguirlo del de base neta")
        self.assertEqual(self.wth_line._ensure_tax(0.6, l10n_ar_tax_type="iibb_total"), tax, "no debe duplicarla")

    def test_ensure_tax_never_resolves_the_cm_variant_for_a_local(self):
        cm_tax = self.wth_line._ensure_tax(0.6, l10n_ar_tax_type="iibb_total")
        cm_tax.sequence = self.wth_tax_untaxed.sequence - 1  # first in search order
        self.wth_tax_untaxed.l10n_ar_tax_type = False
        local_base = self.wth_line._get_parp_tax_type("D")

        self.assertEqual(self.wth_line._ensure_tax(0.6, l10n_ar_tax_type=local_base), self.wth_tax_untaxed)

        new_tax = self.wth_line._ensure_tax(0.9, l10n_ar_tax_type=local_base)
        self.assertNotEqual(new_tax.l10n_ar_tax_type, "iibb_total")
        self.assertNotIn("CM", new_tax.name)

    def test_ensure_tax_keeps_a_configured_total_base_for_a_local(self):
        self.wth_tax_untaxed.l10n_ar_tax_type = "iibb_total"

        tax = self.wth_line._ensure_tax(0.6, l10n_ar_tax_type=self.wth_line._get_parp_tax_type("D"))

        self.assertEqual(tax, self.wth_tax_untaxed)

    def test_ensure_tax_does_not_interfere_outside_santa_fe(self):
        neuquen_group = self.env["account.tax.group"].create(
            {"name": "Test Ret. IIBB Neuquén", "company_id": self.company_ri.id}
        )
        neuquen_vals = {
            "l10n_ar_state_id": self.env.ref("base.state_ar_q").id,
            "tax_group_id": neuquen_group.id,
            "l10n_ar_tax_type": False,
        }
        default_tax = self.wth_tax_untaxed.copy({"name": "Ret. IIBB Neuquén 1.5%", "amount": 1.5, **neuquen_vals})
        total_tax = self.wth_tax_untaxed.copy(
            {"name": "Ret. IIBB Neuquén 2.0%", "amount": 2.0, **neuquen_vals, "l10n_ar_tax_type": "iibb_total"}
        )
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Test Neuquén",
                "company_id": self.company_ri.id,
                "l10n_ar_tax_ids": [Command.create({"default_tax_id": default_tax.id, "tax_type": "withholding"})],
            }
        )

        tax = fiscal_position.l10n_ar_tax_ids._ensure_tax(2.0)

        self.assertEqual(tax, total_tax, "debe reusar el impuesto existente, no crear uno de base neta")

    def test_cm_variant_is_not_selectable_as_default_tax(self):
        cm_tax = self.wth_line._ensure_tax(0.6, l10n_ar_tax_type="iibb_total")
        self.wth_line.invalidate_recordset(["tax_template_domain"])

        selectable = self.env["account.tax"].search(ast.literal_eval(self.wth_line.tax_template_domain))

        self.assertIn(self.wth_tax_untaxed, selectable)
        self.assertNotIn(cm_tax, selectable)

    def test_padron_base_needs_the_padron_aliquot(self):
        self._create_example_padron()
        partner = self._create_partner(CUIT_MULTILATERAL)
        self.assertEqual(self.wth_line._get_padron_tax_type(partner, PAYMENT_DATE), "iibb_total")

        self.wth_line.webservice = "agip"

        self.assertFalse(self.wth_line._get_padron_tax_type(partner, PAYMENT_DATE))

    def test_padron_threads_the_base_down_to_the_tax(self):
        self._create_example_padron()

        with self._without_demo_user():
            cm_tax = self.wth_line._get_tax_from_ws(self._create_partner(CUIT_MULTILATERAL), PAYMENT_DATE)
            local_tax = self.wth_line._get_tax_from_ws(self._create_partner(CUIT_LOCAL), PAYMENT_DATE)
            missing_tax = self.wth_line._get_tax_from_ws(self._create_partner(CUIT_NOT_IN_PADRON), PAYMENT_DATE)

        self.assertEqual((cm_tax.amount, cm_tax.l10n_ar_tax_type), (0.6, "iibb_total"))
        self.assertIn("CM", cm_tax.name)
        self.assertEqual((local_tax.amount, local_tax.l10n_ar_tax_type), (0.8, "iibb_untaxed"))
        self.assertEqual(missing_tax, self.wth_tax_untaxed)
