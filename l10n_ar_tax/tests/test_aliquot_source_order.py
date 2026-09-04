import base64
import io
import shutil
import zipfile
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common


class TestAliquotSourceOrder(common.TransactionCase):
    """El orden de resolución de la alícuota es único para todas las jurisdicciones:
    padrón cargado en la base primero, web service de la jurisdicción después.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.state_caba = cls.env.ref("base.state_ar_c")
        cls.date = fields.Date.start_of(fields.Date.today(), "month")
        cls.to_date = fields.Date.end_of(cls.date, "month")
        cls.cuit = "30112223351"
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "partner padron",
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_cuit").id,
                "vat": cls.cuit,
            }
        )
        tax_group = cls.env["account.tax.group"].create(
            {"name": "IIBB CABA test", "country_id": cls.env.ref("base.ar").id}
        )
        cls.tax_caba = cls.env["account.tax"].create(
            {
                "name": "P. IIBB CABA test",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 3.0,
                "country_id": cls.env.ref("base.ar").id,
                "tax_group_id": tax_group.id,
                "l10n_ar_state_id": cls.state_caba.id,
            }
        )
        cls.fiscal_position = cls.env["account.fiscal.position"].create({"name": "CABA test"})

    def _create_fp_line(self, webservice):
        return self.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": self.fiscal_position.id,
                "default_tax_id": self.tax_caba.id,
                "tax_type": "perception",
                "webservice": webservice,
            }
        )

    def _create_caba_padron(self):
        """Padrón de AGIP: mismo layout que el PARP de Santa Fe (percepción en la columna 7,
        retención en la 8)."""
        line = "d0;d1;d2;%s;d4;d5;d6;%s;%s" % (self.cuit, "4,50", "2,25")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("padron_agip.txt", line + "\n")
        padron = self.env["res.company.jurisdiction.padron"].create(
            {
                "company_id": self.env.company.id,
                "state_id": self.state_caba.id,
                "file_padron": base64.b64encode(buffer.getvalue()).decode(),
                "filename": "padron_agip.zip",
                "l10n_ar_padron_from_date": self.date,
                "l10n_ar_padron_to_date": self.to_date,
            }
        )
        self.addCleanup(shutil.rmtree, padron._get_padron_tmp_dir(), ignore_errors=True)
        return padron

    def _patch_agip_ws(self, result=(9.99, "WS")):
        """El web service de AGIP (el padrón de la base de Adhoc) lo provee
        saas_client_l10n_ar, que no está instalado acá."""
        return patch.object(
            type(self.env["account.fiscal.position.l10n_ar_tax"]),
            "_get_agip_data",
            lambda self, partner, date, to_date: result,
        )

    def test_padron_file_wins_over_webservice(self):
        """Con padrón cargado la alícuota sale del archivo, incluso si la línea está
        configurada para consultar web service (es la contingencia cuando el ws falla)."""
        self._create_caba_padron()
        fp_line = self._create_fp_line("agip")

        with self._patch_agip_ws():
            aliquot, ref, __ = fp_line._unpack_ws_data(fp_line._get_aliquot(self.partner, self.date, self.to_date))

        self.assertEqual(aliquot, 4.5, "la percepción tiene que salir del padrón, no del ws")
        self.assertIn("AGIP", ref)

    def test_webservice_used_when_no_padron_uploaded(self):
        """Sin padrón cargado, una línea con web service lo consulta."""
        fp_line = self._create_fp_line("agip")

        with self._patch_agip_ws():
            aliquot, ref, __ = fp_line._unpack_ws_data(fp_line._get_aliquot(self.partner, self.date, self.to_date))

        self.assertEqual((aliquot, ref), (9.99, "WS"))

    def test_padron_only_never_queries_webservice(self):
        """Configurada como "Archivo de padrón", la línea no consulta web service nunca: sin
        padrón cargado pide que lo carguen."""
        fp_line = self._create_fp_line("padron")

        def fail(self, partner, date, to_date):
            raise AssertionError("no debe consultar el web service")

        with patch.object(type(self.env["account.fiscal.position.l10n_ar_tax"]), "_get_agip_data", fail):
            if self.env.ref("base.user_demo", raise_if_not_found=False):
                # En base demo no hay padrón que cargar (la demo de l10n_ar_account_reports
                # crea líneas de Santa Fe): se devuelve el dummy, tampoco el web service.
                aliquot, ref, __ = fp_line._unpack_ws_data(fp_line._get_aliquot(self.partner, self.date, self.to_date))
                self.assertIn("dummy", ref)
            else:
                with self.assertRaisesRegex(UserError, "No padron uploaded"):
                    fp_line._get_aliquot(self.partner, self.date, self.to_date)

    def test_padron_of_another_period_is_not_used(self):
        """Un padrón de otro período no aplica: se va al web service."""
        padron = self._create_caba_padron()
        padron.write(
            {
                "l10n_ar_padron_from_date": self.date + relativedelta(months=1),
                "l10n_ar_padron_to_date": self.to_date + relativedelta(months=1),
            }
        )
        fp_line = self._create_fp_line("agip")

        with self._patch_agip_ws():
            aliquot, ref, __ = fp_line._unpack_ws_data(fp_line._get_aliquot(self.partner, self.date, self.to_date))

        self.assertEqual((aliquot, ref), (9.99, "WS"))

    def test_partner_without_vat_does_not_read_someone_elses_aliquot(self):
        """Sin CUIT no se busca en el padrón: un vat vacío matchearía cualquier línea."""
        self._create_caba_padron()
        partner_without_vat = self.env["res.partner"].create({"name": "partner sin cuit"})
        fp_line = self._create_fp_line("agip")

        with self._patch_agip_ws():
            with self.assertRaises(UserError):
                fp_line._get_aliquot(partner_without_vat, self.date, self.to_date)

    def test_partner_not_in_padron_falls_back_to_default_tax(self):
        """Si el CUIT no figura en el padrón devolvemos None (la línea usa su impuesto por
        defecto), no la alícuota del web service."""
        self._create_caba_padron()
        other_partner = self.env["res.partner"].create(
            {
                "name": "partner ausente",
                "l10n_latam_identification_type_id": self.env.ref("l10n_ar.it_cuit").id,
                "vat": "30112223335",
            }
        )
        fp_line = self._create_fp_line("agip")

        with self._patch_agip_ws():
            aliquot, ref, __ = fp_line._unpack_ws_data(fp_line._get_aliquot(other_partner, self.date, self.to_date))

        self.assertIsNone(aliquot)
        self.assertIn("Not found in AGIP padron", ref)
