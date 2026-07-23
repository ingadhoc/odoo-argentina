import base64
import io
import shutil
import zipfile

from dateutil.relativedelta import relativedelta
from odoo.tests import common


class TestPadronTmpDir(common.TransactionCase):
    """Padron ARBA extraido a un dir por periodo, no a /tmp compartido."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.padron_model = cls.env["res.company.jurisdiction.padron"]
        cls.state_arba = cls.env.ref("base.state_ar_b")
        cls.cuit_type = cls.env.ref("l10n_ar.it_cuit")
        cls.today = cls.env["res.partner"].create({"name": "dummy"}).create_date.date()

    def _create_partner(self, vat):
        return self.env["res.partner"].create(
            {"name": "partner_%s" % vat, "l10n_latam_identification_type_id": self.cuit_type.id, "vat": vat}
        )

    def _line(self, nro, cuit, aliq):
        return "f0;f1;f2;%s;%s;f5;f6;f7;%s" % (nro, cuit, aliq)

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
