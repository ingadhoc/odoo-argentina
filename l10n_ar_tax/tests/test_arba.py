from unittest import mock

import requests
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common
from odoo.tools import mute_logger


class TestARBA(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner = cls.env["res.partner"].create(
            {
                "name": "test_company",
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_cuit").id,
                "vat": "30697130841",
            }
        )
        company = cls.env["res.company"].create(
            {"name": "test_company", "partner_id": partner.id, "vat": "30697130841"}
        )
        cls.company = company.with_company(company)

    def _arba_consultar(self):
        return self.company.arba_consultar_contribuyente(
            "30697130841",
            fields.Date.start_of(fields.Date.today(), "month"),
            fields.Date.end_of(fields.Date.today(), "month"),
        )

    def test_0_arbaconnect(self):
        with self.assertRaisesRegex(UserError, "You must configure CIT"):
            self._arba_consultar()
        self.company.vat = ""
        with self.assertRaisesRegex(UserError, "No VAT configured"):
            self._arba_consultar()

    @mute_logger("odoo.addons.l10n_ar_tax.models.res_company")
    def test_1_arba_ws_timeout_raises_user_error(self):
        """Si el webservice de ARBA no responde (timeout), la excepcion de red no
        debe propagarse cruda: se traduce a un UserError amigable."""
        self.company.arba_cit = "dummy_cit"
        with mock.patch.object(requests, "post", side_effect=requests.exceptions.Timeout("read timed out")):
            with self.assertRaisesRegex(UserError, "ARBA webservice"):
                self._arba_consultar()

    @mute_logger("odoo.addons.l10n_ar_tax.models.res_company")
    def test_2_arba_ws_connection_error_raises_user_error(self):
        """Idem para cualquier otro error de conexion (RequestException)."""
        self.company.arba_cit = "dummy_cit"
        with mock.patch.object(requests, "post", side_effect=requests.exceptions.ConnectionError("connection refused")):
            with self.assertRaisesRegex(UserError, "ARBA webservice"):
                self._arba_consultar()
