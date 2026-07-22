import base64
import io
import zipfile

from odoo.exceptions import UserError, ValidationError
from odoo.tests import common


class TestARBA(common.TransactionCase):
    def test_0_arbaconnect(self):
        partner = self.env["res.partner"].create(
            {
                "name": "test_company",
                "l10n_latam_identification_type_id": self.env.ref("l10n_ar.it_cuit").id,
                "vat": "30697130841",
            }
        )
        company = self.env["res.company"].create(
            {"name": "test_company", "partner_id": partner.id, "vat": "30697130841"}
        )
        self.env.company = company
        with self.assertRaisesRegex(UserError, "You must configure CIT"):
            self.env.company.arba_connect()
        company.vat = ""
        with self.assertRaisesRegex(UserError, "No VAT configured"):
            self.env.company.arba_connect()

    # -- Helpers para tests de lectura de padrón --------------------------------

    def _zip_b64(self, files):
        """Devuelve un zip (base64) con {nombre: contenido} en memoria."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zip_file:
            for name, content in files.items():
                zip_file.writestr(name, content)
        return base64.b64encode(buffer.getvalue())

    def _padron(self, file_b64):
        """Registro de padrón en memoria (sin persistir) con file_padron seteado."""
        return self.env["res.company.jurisdiction.padron"].new({"file_padron": file_b64})

    def _arba_line(self, cuit, aliquot, nro="NRO"):
        # Formato ARBA: nro en índice 3, cuit en índice 4, alícuota en índice 8
        # (con columnas después, tal como el archivo real; así el índice 8 no
        # arrastra el salto de línea).
        return "0;0;0;%s;%s;0;0;0;%s;GRP;RAZON SOCIAL\n" % (nro, cuit, aliquot)

    # -- Tests del fix de lectura de padrón -------------------------------------

    def test_arba_reads_own_zip(self):
        cuit = "30709328839"
        padron = self._padron(
            self._zip_b64(
                {
                    "PadronRGSPer072026.txt": self._arba_line(cuit, "0,70"),
                    "PadronRGSRet072026.txt": self._arba_line(cuit, "0,90"),
                }
            )
        )
        nro, aliquot_ret, aliquot_per = padron._get_arba_aliquot_from_zip(cuit)
        self.assertTrue(nro)
        self.assertEqual(aliquot_ret, "0.90")
        self.assertEqual(aliquot_per, "0.70")

    def test_arba_no_cross_period_contamination(self):
        """Leer el padrón de un período no debe devolver la alícuota de otro:
        la lectura en memoria usa el file_padron del propio registro."""
        cuit = "30709328839"
        june = self._padron(
            self._zip_b64(
                {
                    "PadronRGSPer062026.txt": self._arba_line(cuit, "2,50"),
                    "PadronRGSRet062026.txt": self._arba_line(cuit, "2,50"),
                }
            )
        )
        july = self._padron(
            self._zip_b64(
                {
                    "PadronRGSPer072026.txt": self._arba_line(cuit, "0,70"),
                    "PadronRGSRet072026.txt": self._arba_line(cuit, "0,90"),
                }
            )
        )
        # Consultar junio primero y luego julio: cada uno devuelve lo suyo.
        june._get_arba_aliquot_from_zip(cuit)
        nro, aliquot_ret, aliquot_per = july._get_arba_aliquot_from_zip(cuit)
        self.assertEqual(aliquot_ret, "0.90")
        self.assertEqual(aliquot_per, "0.70")

    def test_arba_cuit_not_in_padron(self):
        padron = self._padron(
            self._zip_b64(
                {
                    "PadronRGSPer072026.txt": self._arba_line("20111111112", "0,70"),
                    "PadronRGSRet072026.txt": self._arba_line("20111111112", "0,90"),
                }
            )
        )
        nro, aliquot_ret, aliquot_per = padron._get_arba_aliquot_from_zip("30709328839")
        self.assertFalse(nro)

    def test_santa_fe_reads_zip_in_memory(self):
        cuit = "30709328839"
        # Formato PARP: cuit en índice 3, percepción en índice 7, retención en índice 8.
        line = "0;0;0;%s;0;0;0;1,50;2,00\n" % cuit
        padron = self._padron(self._zip_b64({"parp_012026.csv": line}))
        is_in_padron, aliquot_ret, aliquot_per = padron._read_parp_from_binary(cuit)
        self.assertTrue(is_in_padron)
        self.assertEqual(aliquot_per, 1.5)
        self.assertEqual(aliquot_ret, 2.0)

    def test_santa_fe_zip_without_parp_raises(self):
        padron = self._padron(self._zip_b64({"readme.md": "sin datos"}))
        with self.assertRaises(ValidationError):
            padron._read_parp_from_binary("30709328839")
