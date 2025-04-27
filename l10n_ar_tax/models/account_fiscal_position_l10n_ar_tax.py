import json
import logging
import re

import requests
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountFiscalPositionL10nArTax(models.Model):
    _name = "account.fiscal.position.l10n_ar_tax"
    _description = "account.fiscal.position.l10n_ar_tax"

    webservice = fields.Selection(
        [("agip", "AGIP (Regimen General)"), ("arba", "ARBA")],
    )

    def _get_agip_data(self, partner, date, to_date):
        # si es base en data demo devolvemos una alicuota demo para que no falle la demo data
        if self.env.ref("base.user_demo", raise_if_not_found=False):
            return (2.5 if self.tax_type == "withholding" else 3.0, "VALOR DUMMY | dummy")
        raise UserError(_("Falta configuración de credenciales de ADHOC para consulta de " "Alícuotas de AGIP"))

    def _get_arba_data(self, partner, date, to_date):
        self.ensure_one()

        cuit = partner.ensure_vat()
        _logger.info("Getting ARBA data for cuit %s from date %s to date %s" % (date, to_date, cuit))
        ws = self.fiscal_position_id.company_id.arba_connect()
        ws.ConsultarContribuyentes(date.strftime("%Y%m%d"), to_date.strftime("%Y%m%d"), cuit)

        error = False
        msg = False
        if ws.Excepcion:
            error = True
            msg = str((ws.Traceback, ws.Excepcion))
            _logger.error("Padron ARBA: Excepcion %s" % msg)

        # ' Hubo error general de ARBA?
        if ws.CodigoError:
            if ws.CodigoError == "11":
                # we still create the record so we don need to check it again
                # on same period
                _logger.info("CUIT %s not present on padron ARBA" % cuit)
            elif ws.CodigoError == "6":
                error = True
                msg = "%s\n Error %s: %s" % (ws.MensajeError, ws.TipoError, ws.CodigoError)
                _logger.error("Padron ARBA: %s" % msg)
            else:
                error = True
                msg = _("Padron ARBA: %s - %s (%s)") % (ws.MensajeError, ws.TipoError, ws.CodigoError)
                _logger.error("Padron ARBA: %s" % msg)

        if error:
            action = self.env.ref("l10n_ar_tax.act_company_jurisdiction_padron")
            raise RedirectWarning(
                _(
                    "Hubo un error al consultar el Padron ARBA. "
                    "Para solucionarlo puede seguir los siguientes pasos, los cuales explicamos con más detalle en este video:\n %s\n\n"
                    "Tiene las siguientes opciones:\n  1) Intentar nuevamente más tarde\n"
                    "  2) Cargar la alícuota manualmente en el partner en cuestión\n"
                    "  3) Subir el archivo del padrón utilizando el Asistente de carga de padrones.\n\n"
                    "Error obtenido:\n%s\n\n"
                )
                % ("https://docs.google.com/document/d/1Tb_0SGKexakuXMn_0in3Z5zLwoaVOgZhYwhQ7DiFjFw/edit", msg),
                action.id,
                _("Ir a Carga de Padrones"),
            )

        # no ponemos esto, si no viene alicuota es porque es cero entonces
        # if not ws.AlicuotaRetencion or not ws.AlicuotaPercepcion:
        #     raise UserError('No pudimos obtener la AlicuotaRetencion')

        # si no hay numero de comprobante entonces es porque no
        # figura en el padron, aplicamos alicuota no inscripto
        if ws.NumeroComprobante:
            return (
                float(ws.AlicuotaRetencion.replace(",", "."))
                if self.tax_type == "withholding"
                else float(ws.AlicuotaPercepcion.replace(",", ".")),
                "%s | %s | %s"
                % (
                    ws.NumeroComprobante,
                    ws.CodigoHash,
                    ws.GrupoRetencion if self.tax_type == "withholding" else ws.GrupoPercepcion,
                ),
            )
        else:
            return None, ws.CodigoHash

    def _get_rentas_cordoba_data(self, partner, date, to_date):
        """Obtener alícuotas desde app.rentascordoba.gob.ar
        :param partner: El partner sobre el cual trabajamos
        :param date: La fecha del comprobante
        :param from_date: Fecha de inicio de validez de alícuota por defecto
        :param to_date: Fecha de fin de validez de alícuota por defecto
        Devuelve diccionario de datos
        """
        # Datos de prueba para instancias demo
        if self.env.ref("base.user_demo", raise_if_not_found=False):
            return (2.5 if self.tax_type == "withholding" else 3.0, "VALOR DUMMY | dummy")

        _logger.info("Getting withholding data from rentascordoba.gob.ar")

        # Establecer parámetros de solicitud
        url = "https://app.rentascordoba.gob.ar/rentas/rest/svcGetAlicuotas"
        payload = {"body": partner.vat}
        headers = {"content-type": "application/json"}

        # Realizar solicitud
        try:
            r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
            json_body = r.json()
        except requests.exceptions.Timeout:
            msg = self.env._("Timeout error when getting data from rentascordoba.gob.ar")
            _logger.warning("%s" % msg)
            raise UserError("%s" % msg)
        except requests.exceptions.RequestException as e:
            msg = self.env._("Error when contacting rentascordoba.gob.ar. The server answered: \n%s" % str(e))
            _logger.warning("%s" % msg)
            raise UserError("%s" % msg)

        code = json_body.get("errorCod")
        ref = json_body.get("message")

        # Capturar Códigos de Error.
        # 3 => No Inscripto, 2 => No pasible, 1 => CUIT incorrecta, 0 => OK
        # casos como adhoc devuelven 1, no encuentra el cuit.
        # lo consideramos igual que no inscripto (no queremos que de raise)
        # estamos guardando igual en el partner info del mensaje (ref)
        if code in [3, 1]:
            aliquot = None
        elif code == 2:
            aliquot = 0.0
        else:
            dict_alic = json_body.get("sdtConsultaAlicuotas")
            aliquot = (
                float(dict_alic.get("CRD_ALICUOTA_RET"))
                if self.tax_type == "withholding"
                else float(dict_alic.get("CRD_ALICUOTA_PER"))
            )
            # Verificamos si el par_cod no es para los recien inscriptos, que vienen con fecha "0000-00-00"
            if dict_alic.get("CRD_PAR_CODIGO") != "NUE_INS":
                # Verificar que el comprobante tenga fecha dentro de la vigencia
                from_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_INICIO"))
                to_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_FIN"))
                if not (from_date_date <= date <= to_date_date):
                    raise UserError(
                        self.env._(
                            "No se puede obtener automáticamente la alicuota para la fecha %s. Por favor, ingrese la misma manualmente en el partner."
                        )
                        % date
                    )

        return aliquot, ref
