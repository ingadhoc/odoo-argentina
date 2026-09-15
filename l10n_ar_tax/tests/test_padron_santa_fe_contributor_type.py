"""
Tests de la base imponible de la retención de IIBB Santa Fe según el tipo de
contribuyente informado por el padrón PARP.

El PARP informa en la posición 40 del registro (columna E, índice 4 del CSV) si el
sujeto retenido es contribuyente Local ('D') o de Convenio Multilateral ('C'). Ese
dato define la base de la retención (art. 380 de la RG 36/2026 de API Santa Fe):

    * Local ('D')                → base neta, sin IVA        → l10n_ar_tax_type iibb_untaxed
    * Conv. Multilateral ('C')   → total "sin deducción alguna" → l10n_ar_tax_type iibb_total

Antes de este cambio el importador descartaba la columna y siempre aplicaba base neta.

En percepciones la base NO cambia por el régimen de convenio, así que el mapeo sólo
aplica a retenciones.
"""

import base64
import io
import shutil
import zipfile
from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.api import Environment
from odoo.tests import tagged
from odoo.tools import file_path

# CUITs del padrón de ejemplo commiteado en el repo (l10n_ar_tax/doc/padron_santa_fe/)
PARP_EXAMPLE_FILE = "l10n_ar_tax/doc/padron_santa_fe/PARP_999999_ejemplo_padron_santa_fe.csv"
CUIT_MULTILATERAL = "20188192514"  # tipo 'C', alícuota retención 0,60
CUIT_LOCAL = "20203032723"  # tipo 'D', alícuota retención 0,80
CUIT_NOT_IN_PADRON = "30111111118"
# Periodo de vigencia del padron de ejemplo
PADRON_FROM, PADRON_TO = "2026-03-01", "2026-03-31"


@tagged("-at_install", "post_install")
class TestPadronSantaFeContributorType(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.santa_fe = cls.env.ref("base.state_ar_s")

        # Grupo e impuesto de retención de IIBB Santa Fe sobre base neta (el que hoy
        # existe en las bases). El caso de Convenio Multilateral debe derivar de acá.
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

    def _read_example_padron(self, cuit):
        with open(file_path(PARP_EXAMPLE_FILE), encoding="latin-1") as fp:
            return self.env["res.company.jurisdiction.padron"]._read_padron_lines(fp.readlines(), cuit)

    def _create_example_padron(self):
        """Carga el padrón de ejemplo del repo como res.company.jurisdiction.padron.
        Santa Fe sólo acepta ZIP, así que lo comprimimos."""
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
        self.addCleanup(shutil.rmtree, padron._get_padron_tmp_dir(), ignore_errors=True)
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
        """La resolución de alícuota devuelve un dummy si la base tiene demo data, así que
        para ejercitar el camino real hacemos que ese ref no resuelva. Los demás xmlid
        siguen resolviendo normal."""
        real_ref = Environment.ref

        def _ref(env, xml_id, raise_if_not_found=True):
            if xml_id == "base.user_demo":
                return None
            return real_ref(env, xml_id, raise_if_not_found=raise_if_not_found)

        with patch.object(Environment, "ref", _ref):
            yield

    def test_parp_reads_the_contributor_type(self):
        """El parser informa el tipo de contribuyente en vez de descartar la columna."""
        self.assertEqual(self._read_example_padron(CUIT_MULTILATERAL), (True, 0.6, 1.25, "C"))
        self.assertEqual(self._read_example_padron(CUIT_LOCAL), (True, 0.8, 3.25, "D"))
        self.assertEqual(self._read_example_padron(CUIT_NOT_IN_PADRON), (False, False, False, False))

    def test_parp_tax_type_mapping(self):
        """Sólo el Convenio Multilateral desvía la base, y sólo en retenciones. El local no
        pide base: se resuelve la del impuesto configurado en la línea."""
        self.assertEqual(self.wth_line._get_parp_tax_type("C"), "iibb_total")
        self.assertFalse(self.wth_line._get_parp_tax_type("D"))
        self.wth_line.tax_type = "perception"
        self.assertFalse(self.wth_line._get_parp_tax_type("C"))

    def test_ensure_tax_creates_and_reuses_the_cm_variant(self):
        """Un CM con la misma alícuota no cae sobre el impuesto de base neta: se crea la
        variante que retiene sobre el total, y la segunda consulta la reusa."""
        tax = self.wth_line._ensure_tax(0.6, l10n_ar_tax_type="iibb_total")

        self.assertNotEqual(tax, self.wth_tax_untaxed)
        self.assertEqual((tax.amount, tax.l10n_ar_tax_type), (0.6, "iibb_total"))
        self.assertIn("CM", tax.name, "el nombre debe distinguirlo del de base neta")
        self.assertEqual(self.wth_line._ensure_tax(0.6, l10n_ar_tax_type="iibb_total"), tax, "no debe duplicarla")

    def test_ensure_tax_never_resolves_the_cm_variant_for_a_local(self):
        """El local no puede resolver a la variante CM ni derivar de ella: quedaría retenido
        sobre el total con IVA. Tampoco cuando el impuesto configurado tiene la base vacía,
        que es el estado normal (l10n_ar_tax_type no es required ni tiene default)."""
        cm_tax = self.wth_line._ensure_tax(0.6, l10n_ar_tax_type="iibb_total")
        cm_tax.sequence = self.wth_tax_untaxed.sequence - 1  # primera en el orden de búsqueda
        self.wth_tax_untaxed.l10n_ar_tax_type = False
        local_base = self.wth_line._get_parp_tax_type("D")

        self.assertEqual(self.wth_line._ensure_tax(0.6, l10n_ar_tax_type=local_base), self.wth_tax_untaxed)

        # a otra alícuota tampoco puede copiar la variante CM
        new_tax = self.wth_line._ensure_tax(0.9, l10n_ar_tax_type=local_base)
        self.assertNotEqual(new_tax.l10n_ar_tax_type, "iibb_total")
        self.assertNotIn("CM", new_tax.name)

    def test_ensure_tax_keeps_a_configured_total_base_for_a_local(self):
        """Una base total configurada a propósito (proveedor que no discrimina IVA) no la
        pisa el padrón: el local no pide base y se resuelve la de la línea."""
        self.wth_tax_untaxed.l10n_ar_tax_type = "iibb_total"

        tax = self.wth_line._ensure_tax(0.6, l10n_ar_tax_type=self.wth_line._get_parp_tax_type("D"))

        self.assertEqual(tax, self.wth_tax_untaxed)

    def test_ensure_tax_does_not_exclude_a_total_base_outside_a_padron_jurisdiction(self):
        """Donde el padrón no informa el régimen no existe la variante CM: un impuesto sobre
        el total (IVA no discriminado, ej. Neuquén) se reusa como cualquier otro. Excluirlo
        crearía un duplicado que retiene sobre la base neta."""
        neuquen_group = self.env["account.tax.group"].create(
            {"name": "Test Ret. IIBB Neuquén", "company_id": self.company_ri.id}
        )
        # la línea tiene la base vacía, que es el estado normal de las bases instaladas
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

    def test_padron_data_threads_the_base_down_to_the_tax(self):
        """Hilo completo: padrón cargado -> _get_padron_data -> _get_parp_tax_type ->
        _ensure_tax. El CM resuelve al impuesto sobre el total, el local al de base neta y
        el que no figura en padrón no pide base (alícuota de castigo)."""
        self._create_example_padron()

        with self._without_demo_user():
            cm_data = self.wth_line._get_padron_data(self._create_partner(CUIT_MULTILATERAL), PADRON_FROM, PADRON_TO)
            local_data = self.wth_line._get_padron_data(self._create_partner(CUIT_LOCAL), PADRON_FROM, PADRON_TO)
            missing = self.wth_line._get_padron_data(self._create_partner(CUIT_NOT_IN_PADRON), PADRON_FROM, PADRON_TO)

        self.assertEqual((cm_data[0], cm_data[2]), (0.6, "iibb_total"))
        self.assertEqual((local_data[0], local_data[2]), (0.8, False))
        self.assertEqual((missing[0], missing[2]), (None, False))

        cm_tax = self.wth_line._ensure_tax(cm_data[0], l10n_ar_tax_type=cm_data[2])
        self.assertEqual(cm_tax.l10n_ar_tax_type, "iibb_total")
        self.assertEqual(self.wth_line._ensure_tax(0.6, l10n_ar_tax_type=local_data[2]), self.wth_tax_untaxed)
