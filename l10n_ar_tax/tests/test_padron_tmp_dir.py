import base64
import io
import shutil
import tempfile
import zipfile
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
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
        self.addCleanup(shutil.rmtree, padron._get_padron_tmp_dir(), ignore_errors=True)
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
        self.addCleanup(shutil.rmtree, padron._get_padron_tmp_dir(), ignore_errors=True)
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
