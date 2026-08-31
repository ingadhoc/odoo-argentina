##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from contextlib import contextmanager
from unittest.mock import patch

import requests
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import common, tagged
from odoo.tools import mute_logger

WS_LOGGER = "odoo.addons.l10n_ar_tax.models.account_fiscal_position_l10n_ar_tax"

NON_JSON_BODY = "<html><body>Servicio no disponible</body></html>"


class RentasCordobaWsMixin:
    """Helpers para simular respuestas del webservice de Rentas Córdoba sin salir a la provincia."""

    @contextmanager
    def _without_demo_shortcut(self):
        """Los métodos del webservice devuelven alícuotas dummy si existe `base.user_demo`.

        Las bases de test lo tienen, así que sin esto no se llega nunca al request. Neutralizamos
        solo ese xmlid, sin tocar datos ni cachés: cualquier otro `env.ref` sigue igual.
        """
        model_data = type(self.env["ir.model.data"])
        original = model_data._xmlid_to_res_model_res_id

        def _fake(self, xmlid, raise_if_not_found=False):
            if xmlid == "base.user_demo":
                return (False, False)
            return original(self, xmlid, raise_if_not_found=raise_if_not_found)

        with patch.object(model_data, "_xmlid_to_res_model_res_id", _fake):
            self.assertFalse(self.env.ref("base.user_demo", raise_if_not_found=False))
            yield

    @contextmanager
    def _ws_answers(self, status_code=200, body="", exception=None):
        response = requests.Response()
        response.status_code = status_code
        response._content = body.encode()

        def _fake_post(*args, **kwargs):
            if exception:
                raise exception
            return response

        with self._without_demo_shortcut(), patch.object(requests, "post", _fake_post):
            yield


class TestRentasCordobaWsErrors(RentasCordobaWsMixin, common.TransactionCase):
    """Una respuesta rota del webservice de Rentas Córdoba llega al usuario como UserError.

    Los registros van con `new()` porque el método solo lee `self.tax_type` y `partner.vat`: así el
    test no depende del plan de cuentas ni de las restricciones de la posición fiscal.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fp_tax = cls.env["account.fiscal.position.l10n_ar_tax"].new(
            {"webservice": "rentas_cordoba", "tax_type": "perception"}
        )
        cls.partner = cls.env["res.partner"].new({"name": "Rentas Cordoba Test", "vat": "30697130841"})
        cls.date = cls.env.cr.now().date()

    def _get_data(self):
        return self.fp_tax._get_rentas_cordoba_data(self.partner, self.date, self.date)

    @mute_logger(WS_LOGGER)
    def test_non_json_body_raises_user_error(self):
        """Ticket 126698: el webservice caído contesta HTML con status 200 y `r.json()` explotaba."""
        with self._ws_answers(status_code=200, body=NON_JSON_BODY):
            with self.assertRaises(UserError):
                self._get_data()

    @mute_logger(WS_LOGGER)
    def test_empty_body_raises_user_error(self):
        """Un body vacío también rompe el decode: es el otro modo de falla que vimos en producción."""
        with self._ws_answers(status_code=200, body=""):
            with self.assertRaises(UserError):
                self._get_data()

    @mute_logger(WS_LOGGER)
    def test_http_error_raises_user_error(self):
        """Cualquier status de error corta antes del decode, no solo el 404 que se chequeaba antes."""
        with self._ws_answers(status_code=503, body="<html>maintenance</html>"):
            with self.assertRaises(UserError):
                self._get_data()

    @mute_logger(WS_LOGGER)
    def test_timeout_raises_user_error(self):
        with self._ws_answers(exception=requests.exceptions.Timeout("timed out")):
            with self.assertRaises(UserError):
                self._get_data()

    def test_valid_json_is_still_read(self):
        """El camino feliz no cambia: un no inscripto sigue devolviendo alícuota vacía y su mensaje."""
        message = "La CUIT ingresada no es correcta o no se encuentra registrada"
        with self._ws_answers(status_code=200, body='{"errorCod": 3, "message": "%s"}' % message):
            aliquot, ref = self._get_data()

        self.assertIsNone(aliquot, "Un no inscripto no tiene alícuota")
        self.assertEqual(ref, message)


@tagged("post_install", "-at_install")
class TestRentasCordobaFiscalPosition(RentasCordobaWsMixin, TestArCommon):
    """La falla del webservice viaja como UserError por la cadena de la posición fiscal.

    Los tests de arriba llaman al método del webservice directo. Acá entramos por
    `_l10n_ar_add_taxes`, que es el punto por el que lo consultan los comprobantes y el onchange de
    la orden de venta: se verifica que el UserError propague hasta el llamador y no se transforme en
    otra excepción en el camino.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # la percepcion del plan viene con alicuota 0, y _l10n_ar_add_taxes descarta las que valen 0:
        # copiamos con una alicuota real para que el impuesto por defecto sea observable en el retorno
        cls.perception_tax = cls.tax_perc_iibb.copy(
            {"name": "Percepcion IIBB Cordoba Test 3%", "amount": 3.0, "active": True}
        )
        cls.fiscal_position = cls.env["account.fiscal.position"].create(
            {
                "name": "Percepcion Cordoba por webservice",
                "company_id": cls.company_ri.id,
                "l10n_ar_tax_ids": [
                    Command.create(
                        {
                            "webservice": "rentas_cordoba",
                            "tax_type": "perception",
                            "default_tax_id": cls.perception_tax.id,
                        }
                    )
                ],
            }
        )
        # el partner no tiene percepciones cargadas, así que la cadena sale a consultar el webservice
        cls.partner = cls.res_partner_adhoc
        cls.date = cls.env.cr.now().date()

    def _add_taxes(self):
        return self.fiscal_position._l10n_ar_add_taxes(self.partner, self.company_ri, self.date, "perception")

    @mute_logger(WS_LOGGER)
    def test_broken_ws_reaches_the_caller_as_user_error(self):
        with self._ws_answers(status_code=200, body=NON_JSON_BODY):
            with self.assertRaises(UserError):
                self._add_taxes()

    def test_partner_without_aliquot_falls_back_to_default_tax(self):
        """Con el webservice respondiendo, un no inscripto deja la percepción por defecto."""
        with self._ws_answers(status_code=200, body='{"errorCod": 3, "message": "No inscripto"}'):
            taxes = self._add_taxes()

        self.assertEqual(taxes, self.perception_tax)
