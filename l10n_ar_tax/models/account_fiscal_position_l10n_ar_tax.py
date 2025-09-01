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

    fiscal_position_id = fields.Many2one("account.fiscal.position", required=True, ondelete="cascade")
    # ponemos default a los selectio porque al ser requeridos si no se comporta raro y parece que elige uno por defecto
    # pero que no esta seleccionado
    webservice = fields.Selection(
        [("agip", "AGIP (Regimen General)"), ("arba", "ARBA"), ("rentas_cordoba", "Rentas Cordoba")],
    )
    tax_template_domain = fields.Char(compute="_compute_tax_template_domain")
    default_tax_id = fields.Many2one("account.tax", required=True)
    tax_type = fields.Selection(
        [("withholding", "Withholding"), ("perception", "Perception")], required=True, default="withholding"
    )

    @api.constrains("fiscal_position_id", "default_tax_id")
    def _check_tax_group_overlap(self):
        for record in self:
            domain = [
                ("id", "!=", record.id),
                ("fiscal_position_id", "=", record.fiscal_position_id.id),
                ("default_tax_id.tax_group_id", "=", record.default_tax_id.tax_group_id.id),
            ]
            if record.tax_type == "withholding":
                # TODO esto lo deberiamos borrar al ir a odoo 19 y solo usar los tax groups
                # por ahora, para no renegar con scripts de migra que requieran crear tax groups para cada jurisdiccion y
                # ademas luego tener que ajustar a lo que hagamos en 19, usamos la jursdiccion como elemento de agrupacion
                # solo para retenciones
                domain += [("default_tax_id.l10n_ar_state_id", "=", record.default_tax_id.l10n_ar_state_id.id)]
            conflicting_records = self.search(domain)
            if conflicting_records:
                raise ValidationError("No puede haber dos impuestos del mismo grupo para la misma posicion fiscal.")

    def _get_missing_taxes(self, partner, date):
        taxes = self.env["account.tax"]
        for rec in self:
            if rec.webservice:
                taxes += rec.sudo()._get_tax_from_ws(partner, date)
            else:
                taxes += rec.default_tax_id
        return taxes

    @api.depends("fiscal_position_id", "tax_type")
    def _compute_tax_template_domain(self):
        for rec in self:
            rec.tax_template_domain = rec._get_tax_domain(filter_tax_group=False)

    def _get_tax_domain(self, filter_tax_group=True):
        self.ensure_one()
        domain = self.env["account.tax"]._check_company_domain(self.fiscal_position_id.company_id)
        domain += [("amount_type", "in", ["percent", "division"])]
        if filter_tax_group:
            domain += [("tax_group_id", "=", self.default_tax_id.tax_group_id.id)]
            if self.tax_type == "withholding":
                # TODO esto lo deberiamos borrar al ir a odoo 19 y solo usar los tax groups
                # por ahora, para no renegar con scripts de migra que requieran crear tax groups para cada jurisdiccion y
                # ademas luego tener que ajustar a lo que hagamos en 19, usamos la jursdiccion como elemento de agrupacion
                # solo para retenciones
                domain += [("l10n_ar_state_id", "=", self.default_tax_id.l10n_ar_state_id.id)]
        if self.tax_type == "perception":
            domain += [("type_tax_use", "=", "sale")]
        elif self.tax_type == "withholding":
            # por ahora los 3 ws usan iibb_untaxed por eso esta hardcodeado
            domain += [("l10n_ar_withholding_payment_type", "=", "supplier")]
            # domain += [WTH Tax = iibb untaxed, (Arg with type = supplier), (type = none)]
        return domain

    def _ensure_tax(self, rate):
        self.ensure_one()
        domain = self._get_tax_domain()
        tax = self.env["account.tax"].with_context(active_test=False).search(domain + [("amount", "=", rate)], limit=1)
        if not tax.active:
            tax.active = True
        if not tax:
            if "%" not in self.default_tax_id.name:
                name = f"{self.default_tax_id.name} {rate}%"
            else:
                # Usamos re.sub para reemplazar el patrón con el nuevo número seguido de '%'
                # Si ya tiene un porcentaje, lo reemplazamos
                name = re.sub(r"\b\d+(\.\d+)?\s*%", f"{rate}%", self.default_tax_id.name)

            tax = self.default_tax_id.copy(
                default={
                    # dejamos sequencia mas baja para que siempre el que se duplica sea el que esta arriba
                    "sequence": 10,
                    "amount": rate,
                    "active": True,
                    "name": name,
                }
            )
        return tax

    def _get_tax_from_ws(self, partner, date):
        self.ensure_one()
        from_date = date + relativedelta(day=1)
        to_date = from_date + relativedelta(days=-1, months=+1)
        aliquot, ref = getattr(self, "_get_%s_data" % self.webservice)(partner, from_date, to_date)
        # devolvemos None si es no inscripto
        if aliquot is None:
            tax = self.default_tax_id
        else:
            tax = self._ensure_tax(aliquot)
        # por mas que sea no inscripto creamos partner aliquot porque si no en cada
        # nueva linea o cambio se conecta a ws
        if self.env.ref("base.user_demo", raise_if_not_found=False):
            # Fix para que al cargar data demo al instalar demo_base_minimal no se termine creando 2 veces
            # los mismos registros de 'l10n_ar.partner.tax'
            if self.env["l10n_ar.partner.tax"].search(
                [
                    ("partner_id", "=", partner.id),
                    ("tax_id", "=", tax.id),
                    ("from_date", "=", from_date),
                    ("to_date", "=", to_date),
                    ("ref", "=", ref),
                ]
            ):
                return self.env["account.tax"]
            # Fix para que al impuesto de demo 'P. IIBB CABA 3.0%' se le agregue la jurisdicción
            if (
                tax.tax_group_id
                == self.env.ref("account.%s_ri_tax_percepcion_iibb_caba_aplicada" % tax.company_id.id).tax_group_id
            ):
                tax.l10n_ar_state_id = self.env.ref("base.state_ar_c")
        self.env["l10n_ar.partner.tax"].create(
            {
                "partner_id": partner.id,
                "tax_id": tax.id,
                "from_date": from_date,
                "to_date": to_date,
                "ref": ref,
            }
        )
        return tax

    def _get_agip_data(self, partner, date, to_date):
        # si es base en data demo devolvemos una alicuota demo para que no falle la demo data
        if self.env.ref("base.user_demo", raise_if_not_found=False):
            return (2.5 if self.tax_type == "withholding" else 3.0, "VALOR DUMMY | dummy")
        raise UserError(_("Falta configuración de credenciales de ADHOC para consulta de Alícuotas de AGIP"))

    def _get_arba_data(self, partner, date, to_date):
        """Metodo que obtiene la alicuota de ARBA de un partner y fecha dado

        :return: (float, string) alícuota y referencia

        donde:
            float valor alicuota (retencion o percepcion depende del caso)
            string "numero comprobante codigohast GrupoRetencion/Percepcion"

        Si hay un padron de alicuotas ya cargado en el sistema, lo usamos
        para obtener la alícuota, sino consultamos el webservice de ARBA
        """
        self.ensure_one()

        cuit = partner.ensure_vat()
        _logger.info("Getting ARBA data for cuit %s from date %s to date %s" % (date, to_date, cuit))

        padron_file = self.env["res.company.jurisdiction.padron"].search(
            [
                ("state_id", "in", self.env.ref("base.state_ar_b").ids),
                ("company_id", "=", self.fiscal_position_id.company_id.id),
                "|",
                ("l10n_ar_padron_from_date", "=", False),
                ("l10n_ar_padron_from_date", "<=", date),
                "|",
                ("l10n_ar_padron_to_date", "=", False),
                ("l10n_ar_padron_to_date", ">=", date),
            ],
            limit=1,
        )
        if padron_file:
            nro, alicuot_ret, alicuot_per = padron_file._get_aliquit(partner)
            if nro:
                return (
                    float(alicuot_ret.replace(",", "."))
                    if self.tax_type == "withholding"
                    else float(alicuot_per.replace(",", ".")),
                    "Alicuota (archivo importado)",
                )
            else:
                return None, "Alícuota no inscripto (archivo importado)"

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
            tax_data = "%s | %s | %s" % (
                ws.NumeroComprobante,
                ws.CodigoHash,
                ws.GrupoRetencion if self.tax_type == "withholding" else ws.GrupoPercepcion,
            )
            if self.tax_type == "withholding":
                return (float(ws.AlicuotaRetencion.replace(",", ".")) if ws.AlicuotaRetencion else None, tax_data)
            else:
                return (float(ws.AlicuotaPercepcion.replace(",", ".")) if ws.AlicuotaPercepcion else None, tax_data)
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

        error_msg = self.env._(
            "No pudimos obtener la alicuota del webservice de rentascordoba.\n\n"
            "Para asignar la alícuota de Córdoba a un contacto, siga estos pasos:\n"
            "1) Consulte la alícuota del contacto en: https://www.rentascordoba.gob.ar/gestiones/consulta-alicuota\n"
            "2) Cree manualmente la alícuota en la vista formulario del Contacto (solapa 'Contabilidad').\n\n"
            "En caso de dudas o si el problema persiste, comuníquese con nuestro equipo de Servicio de Asistencia.\n"
            "Detalle del error:\n"
        )

        # Realizar solicitud
        try:
            r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
        except requests.exceptions.Timeout as e:
            msg = self.env._(error_msg + "Timeout error when getting data.")
            _logger.warning("%s" % str(e))
            raise UserError("%s" % msg)
        except requests.exceptions.RequestException as e:
            _logger.warning("%s" % str(e))
            raise UserError("%s" % error_msg)
        if r.status_code == 404:
            msg = _(error_msg + "404 Not Found error.")
            raise UserError("%s" % msg)
        json_body = r.json()
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
