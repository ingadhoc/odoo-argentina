import base64
import io
import shutil
import zipfile
from datetime import timedelta
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from odoo.tests import common


class TestPadronAliquot(common.TransactionCase):
    """Track 1: lookup awk columna exacta + caché por-CUIT + fix re-decode Santa Fe."""

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
            {
                "name": "partner_%s" % vat,
                "l10n_latam_identification_type_id": self.cuit_type.id,
                "vat": vat,
            }
        )

    def _create_arba_padron(self, per_lines, ret_lines, from_date=None, to_date=None):
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
                "l10n_ar_padron_from_date": from_date or self.today + relativedelta(days=-1),
                "l10n_ar_padron_to_date": to_date or self.today + relativedelta(days=30),
            }
        )
        self.addCleanup(shutil.rmtree, padron._get_parp_tmp_dir(), ignore_errors=True)
        return padron

    def _create_santa_fe_padron(self, parp_lines):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("PARP072026.TXT", "\n".join(parp_lines) + "\n")
        padron = self.padron_model.create(
            {
                "company_id": self.env.company.id,
                "state_id": self.state_santa_fe.id,
                "file_padron": base64.b64encode(buffer.getvalue()).decode(),
                "filename": "padron_santafe.zip",
                "l10n_ar_padron_from_date": self.today + relativedelta(days=-1),
                "l10n_ar_padron_to_date": self.today + relativedelta(days=30),
            }
        )
        self.addCleanup(shutil.rmtree, padron._get_parp_tmp_dir(), ignore_errors=True)
        return padron

    def test_arba_lookup_matches_exact_column_not_substring(self):
        """El CUIT decoy es substring de otro campo; awk no debe matchearlo."""
        cuit = "30112223335"
        decoy_per = "d0;d1;d2;DECOY;RAZON%sSA;d5;d6;d7;99,99" % cuit
        real_per = "f0;f1;f2;NRO456;%s;f5;f6;f7;12,50" % cuit
        decoy_ret = "d0;d1;d2;DECOY;RAZON%sSA;d5;d6;d7;88,88" % cuit
        real_ret = "f0;f1;f2;NRO789;%s;f5;f6;f7;7,00" % cuit
        padron = self._create_arba_padron([decoy_per, real_per], [decoy_ret, real_ret])
        partner = self._create_partner(cuit)

        nro, aliquot_ret, aliquot_per = padron._get_aliquot(partner)

        self.assertEqual(nro, "NRO789")
        self.assertEqual(aliquot_per, "12.50")
        self.assertEqual(aliquot_ret, "7.00")

    def test_arba_different_months_do_not_share_extracted_files(self):
        """Dos padrones de distinto mes no deben devolver la alícuota del otro."""
        cuit = "30112223351"
        padron_1 = self._create_arba_padron(
            ["f0;f1;f2;NRO-1;%s;f5;f6;f7;11,00" % cuit],
            ["f0;f1;f2;NRO-1;%s;f5;f6;f7;1,00" % cuit],
            from_date=self.today,
            to_date=self.today + relativedelta(days=30),
        )
        padron_2 = self._create_arba_padron(
            ["f0;f1;f2;NRO-2;%s;f5;f6;f7;22,00" % cuit],
            ["f0;f1;f2;NRO-2;%s;f5;f6;f7;2,00" % cuit],
            from_date=self.today + relativedelta(months=1),
            to_date=self.today + relativedelta(months=1, days=30),
        )
        partner = self._create_partner(cuit)

        self.assertEqual(padron_1._get_aliquot(partner), ("NRO-1", "1.00", "11.00"))
        self.assertEqual(padron_2._get_aliquot(partner), ("NRO-2", "2.00", "22.00"))

    def test_get_aliquot_caches_by_cuit_and_invalidates_on_write_date(self):
        """Cache hit en la 2da consulta; write_date nuevo invalida la caché."""
        cuit = "30112223343"
        per_line = "f0;f1;f2;NRO456;%s;f5;f6;f7;12,50" % cuit
        ret_line = "f0;f1;f2;NRO789;%s;f5;f6;f7;7,00" % cuit
        padron = self._create_arba_padron([per_line], [ret_line])
        partner = self._create_partner(cuit)

        original_find_aliquot = type(padron).find_aliquot
        calls = []

        def counting_find_aliquot(self, path, cuit):
            calls.append(1)
            return original_find_aliquot(self, path, cuit)

        with patch.object(type(padron), "find_aliquot", counting_find_aliquot):
            padron._get_aliquot(partner)
            padron._get_aliquot(partner)
            self.assertEqual(
                len(calls), 2, "Segunda consulta del mismo CUIT debe ser cache hit (Per+Ret solo la 1ra vez)"
            )

            # write() no sirve acá: Odoo memoiza now() por cursor, mismo write_date en la
            # misma transacción. Simulamos un reload real pisando write_date por SQL.
            new_write_date = padron.write_date + timedelta(seconds=1)
            self.env.cr.execute(
                "UPDATE res_company_jurisdiction_padron SET write_date = %s WHERE id = %s",
                (new_write_date, padron.id),
            )
            padron.invalidate_recordset(["write_date"])
            padron._get_aliquot(partner)
            self.assertEqual(len(calls), 4, "write_date nuevo debe invalidar la caché y volver a ejecutar el lookup")

    def test_santa_fe_does_not_redecode_binary_on_second_cuit(self):
        """El binario se extrae una sola vez, no por cada CUIT consultado."""
        cuit_a = "20222333440"
        cuit_b = "20222333459"
        line_a = "01012026;01012026;31122026; %s ;RI;A;S;5,00;3,00;G1;G2;RAZON A" % cuit_a
        line_b = "01012026;01012026;31122026; %s ;RI;A;S;7,50;4,25;G1;G2;RAZON B" % cuit_b
        padron = self._create_santa_fe_padron([line_a, line_b])
        partner_a = self._create_partner(cuit_a)
        partner_b = self._create_partner(cuit_b)

        original_descompress = type(padron).descompress_file
        calls = []

        def counting_descompress(self, file_padron, dest_dir="/tmp"):
            calls.append(1)
            return original_descompress(self, file_padron, dest_dir=dest_dir)

        with patch.object(type(padron), "descompress_file", counting_descompress):
            is_in_padron_a, aliquot_ret_a, aliquot_per_a = padron._get_aliquot(partner_a)
            is_in_padron_b, aliquot_ret_b, aliquot_per_b = padron._get_aliquot(partner_b)

        self.assertEqual(len(calls), 1, "El binario no debe re-decodificarse/re-unzipearse en la 2da consulta")
        self.assertTrue(is_in_padron_a)
        self.assertEqual((aliquot_ret_a, aliquot_per_a), (3.0, 5.0))
        self.assertTrue(is_in_padron_b)
        self.assertEqual((aliquot_ret_b, aliquot_per_b), (4.25, 7.5))
