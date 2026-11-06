import base64
import io
import os
import shutil
import tempfile
import zipfile
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tests import common


class TestPadronTmpDir(common.TransactionCase):
    """Padron ARBA extraido a un dir por periodo, no a /tmp compartido."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.padron_model = cls.env["res.company.jurisdiction.padron"]
        cls.state_arba = cls.env.ref("base.state_ar_b")
        cls.state_santa_fe = cls.env.ref("base.state_ar_s")
        cls.cuit_type = cls.env.ref("l10n_ar.it_cuit")
        cls.today = cls.env["res.partner"].create({"name": "dummy"}).create_date.date()

    def _create_partner(self, vat):
        return self.env["res.partner"].create(
            {"name": "partner_%s" % vat, "l10n_latam_identification_type_id": self.cuit_type.id, "vat": vat}
        )

    def _line(self, nro, cuit, aliq):
        return "f0;f1;f2;%s;%s;f5;f6;f7;%s" % (nro, cuit, aliq)

    def _parp_line(self, cuit, per, ret):
        return "d0;d1;d2;%s;d4;d5;d6;%s;%s" % (cuit, per, ret)

    def _create_arba_padron(self, per_lines, ret_lines, from_date, to_date):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("Per.TXT", "\n".join(per_lines) + "\n")
            zip_file.writestr("Ret.TXT", "\n".join(ret_lines) + "\n")
        padron = self.padron_model.create(
            {
                "company_id": self.env.company.id,
                "state_id": self.state_arba.id,
                "file_padron": base64.b64encode(buffer.getvalue()).decode(),
                "filename": "padron_arba.zip",
                "l10n_ar_padron_from_date": from_date,
                "l10n_ar_padron_to_date": to_date,
            }
        )
        self.addCleanup(shutil.rmtree, padron._get_parp_tmp_dir(), ignore_errors=True)
        return padron

    def _create_santa_fe_padron(self, lines):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("PARP.TXT", "\n".join(lines) + "\n")
        padron = self.padron_model.create(
            {
                "company_id": self.env.company.id,
                "state_id": self.state_santa_fe.id,
                "file_padron": base64.b64encode(buffer.getvalue()).decode(),
                "filename": "padron_santafe.zip",
                "l10n_ar_padron_from_date": self.today,
                "l10n_ar_padron_to_date": self.today + relativedelta(days=30),
            }
        )
        self.addCleanup(shutil.rmtree, padron._get_parp_tmp_dir(), ignore_errors=True)
        return padron

    def test_arba_different_months_do_not_share_extracted_files(self):
        """Dos padrones de distinto mes no deben devolver la alícuota del otro."""
        cuit = "30112223351"
        padron_1 = self._create_arba_padron(
            [self._line("NRO-1", cuit, "11,00")],
            [self._line("NRO-1", cuit, "1,00")],
            self.today,
            self.today + relativedelta(days=30),
        )
        padron_2 = self._create_arba_padron(
            [self._line("NRO-2", cuit, "22,00")],
            [self._line("NRO-2", cuit, "2,00")],
            self.today + relativedelta(months=1),
            self.today + relativedelta(months=1, days=30),
        )
        partner = self._create_partner(cuit)

        self.assertEqual(padron_1._get_aliquot(partner), ("NRO-1", "1.00", "11.00"))
        self.assertEqual(padron_2._get_aliquot(partner), ("NRO-2", "2.00", "22.00"))

    def test_partner_without_cuit_is_not_in_padron(self):
        """Un contacto sin CUIT (ej. consumidor final con DNI) no está en el padrón y no bloquea."""
        padron = self._create_santa_fe_padron([self._parp_line("20222333440", "5,00", "3,00")])
        partner = self.env["res.partner"].create(
            {
                "name": "partner dni",
                "l10n_latam_identification_type_id": self.env.ref("l10n_ar.it_dni").id,
                "vat": "22333444",
            }
        )
        self.assertEqual(padron._get_aliquot(partner), (False, 0.0, 0.0))

    def test_santa_fe_does_not_redecode_binary_on_second_cuit(self):
        """El binario se extrae una sola vez, no por cada CUIT consultado."""
        cuit_a, cuit_b = "20222333440", "20222333459"
        padron = self._create_santa_fe_padron(
            [self._parp_line(cuit_a, "5,00", "3,00"), self._parp_line(cuit_b, "7,50", "4,25")]
        )
        partner_a = self._create_partner(cuit_a)
        partner_b = self._create_partner(cuit_b)

        calls = []
        original = type(padron).descompress_file

        def counting(self, file_padron, dest_dir="/tmp"):
            calls.append(1)
            return original(self, file_padron, dest_dir=dest_dir)

        with patch.object(type(padron), "descompress_file", counting):
            result_a = padron._get_aliquot(partner_a)
            result_b = padron._get_aliquot(partner_b)

        self.assertEqual(len(calls), 1, "no debe re-decodificar/re-unzipear en la 2da consulta")
        self.assertEqual(result_a, (True, 3.0, 5.0))
        self.assertEqual(result_b, (True, 4.25, 7.5))

    def test_find_aliquot_ignores_substring_match(self):
        """El CUIT aparece embebido en otro campo en la 1ra linea; debe matchear la exacta."""
        cuit = "30112223335"
        content = "%s\n%s\n" % (
            self._line("DECOY", "RAZON%sSA" % cuit, "99,99"),
            self._line("NRO789", cuit, "7,00"),
        )
        with tempfile.NamedTemporaryFile("w", suffix=".txt") as f:
            f.write(content)
            f.flush()
            nro, aliq = self.padron_model.find_aliquot(f.name, cuit)

        self.assertEqual((nro, aliq), ("NRO789", "7,00"))

    def test_extraction_does_not_leave_zip_copy_in_tmp(self):
        """Descomprimir no deja en /tmp la copia temporal del zip."""
        cuit = "30112223351"
        padron = self._create_arba_padron(
            [self._line("NRO-1", cuit, "11,00")],
            [self._line("NRO-1", cuit, "1,00")],
            self.today,
            self.today + relativedelta(days=30),
        )
        partner = self._create_partner(cuit)
        # Own temp dir: other processes may write to the shared /tmp while the test runs.
        tmp_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_root, ignore_errors=True)

        with patch.object(tempfile, "tempdir", tmp_root):
            padron._get_aliquot(partner)

        self.assertFalse(os.listdir(tmp_root))

    def _fixed_line(self, kind, cuit, aliq):
        # Same layout as the real ARBA files: every line has the same length and CUITs are sorted.
        return "%s;29102026;01112026;30112026;%s;D;N;N;%s;01;" % (kind, cuit, aliq)

    def _write_padron_file(self, lines):
        fp = tempfile.NamedTemporaryFile("w", suffix=".TXT", delete=False)
        self.addCleanup(os.remove, fp.name)
        with fp:
            fp.write("\n".join(lines) + "\n")
        return fp.name

    def test_sorted_fixed_width_padron_is_bisected(self):
        """Un padrón ordenado y de ancho fijo se busca por bisección, sin grep."""
        cuits = ["20000033481", "20111222333", "27222333444", "30112223351", "33999888775"]
        path = self._write_padron_file([self._fixed_line("R", c, "%d,50" % i) for i, c in enumerate(cuits)])

        with patch("subprocess.run", side_effect=AssertionError("grep should not run")):
            for i, cuit in enumerate(cuits):
                self.assertEqual(self.padron_model.find_aliquot(path, cuit), ("30112026", "%d,50" % i))
            self.assertEqual(self.padron_model.find_aliquot(path, "30112223352"), (False, False))
            self.assertEqual(self.padron_model.find_aliquot(path, "2000003348"), (False, False))

    def test_unsorted_padron_falls_back_to_grep(self):
        """Si el padrón no viene ordenado por CUIT, la consulta usa grep y encuentra igual."""
        cuits = ["30112223351", "20000033481", "27222333444"]
        path = self._write_padron_file([self._fixed_line("R", c, "1,00") for c in cuits])

        self.assertFalse(self.padron_model._get_padron_layout(path))
        for cuit in cuits:
            self.assertEqual(self.padron_model.find_aliquot(path, cuit), ("30112026", "1,00"))

    def test_variable_width_padron_falls_back_to_grep(self):
        """Si las líneas no miden todas lo mismo, la consulta usa grep y encuentra igual."""
        path = self._write_padron_file(
            [self._fixed_line("R", "20000033481", "1,00"), self._fixed_line("R", "30112223351", "10,00")]
        )

        self.assertFalse(self.padron_model._get_padron_layout(path))
        self.assertEqual(self.padron_model.find_aliquot(path, "30112223351"), ("30112026", "10,00"))

    def test_find_aliquot_raises_when_padron_cannot_be_read(self):
        """Si grep no puede leer el archivo, da error en vez de devolver que el CUIT no figura."""
        with self.assertRaises(UserError):
            self.padron_model.find_aliquot("/nonexistent/l10n_ar_padron.txt", "30112223351")
