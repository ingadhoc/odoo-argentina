import json
import logging
import re

import requests
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountFiscalPositionL10nArTax(models.Model):
    _name = "account.fiscal.position.l10n_ar_tax"
    _description = "account.fiscal.position.l10n_ar_tax"

    fiscal_position_id = fields.Many2one("account.fiscal.position", required=True, ondelete="cascade")
    company_id = fields.Many2one("res.company", related="fiscal_position_id.company_id", store=True)
    # ponemos default a los selection porque al ser requeridos si no se comporta raro y parece que elige uno por defecto
    # pero que no esta seleccionado
    webservice = fields.Selection(
        [
            ("agip", "AGIP (Regimen General)"),
            ("arba", "ARBA"),
            ("rentas_cordoba", "Rentas Cordoba"),
            ("padron", "Archivo de padrón"),
        ],
    )
    tax_template_domain = fields.Char(compute="_compute_tax_template_domain")
    default_tax_id = fields.Many2one("account.tax", required=True)
    tax_type = fields.Selection(
        [("withholding", "Withholding"), ("perception", "Perception")],
        required=True,
        default=lambda self: self.env.context.get("default_tax_type", "withholding"),
    )
    tax_group_id = fields.Many2one(
        "account.tax.group",
        string="Tax Group",
        compute="_compute_tax_group_id",
        inverse="_inverse_tax_group_aliquot",
        check_company=True,
    )
    aliquot = fields.Float(
        string="Aliquot (%)",
        digits=(5, 2),
        compute="_compute_aliquot",
        inverse="_inverse_tax_group_aliquot",
    )
    tax_group_id_domain = fields.Char(compute="_compute_tax_group_id_domain")
    l10n_ar_is_iibb = fields.Boolean(compute="_compute_l10n_ar_is_iibb")

    @api.depends("tax_group_id")
    def _compute_l10n_ar_is_iibb(self):
        for rec in self:
            rec.l10n_ar_is_iibb = bool(rec.tax_group_id.tax_ids.filtered(lambda t: t.l10n_ar_state_id))

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

    @api.constrains("webservice", "default_tax_id")
    def _check_webservice_available(self):
        for record in self:
            if record.webservice == "padron":
                if not record.default_tax_id.l10n_ar_state_id:
                    raise ValidationError(
                        "Impuesto %s sin provincia establecida, no puede consultar padrón" % record.default_tax_id.name
                    )
                if record.default_tax_id.l10n_ar_state_id.jurisdiction_code not in ["902", "921"]:
                    raise ValidationError(
                        "Padrón no implementado para la provincia de %s." % record.default_tax_id.l10n_ar_state_id.name
                    )

    def _get_missing_taxes(self, partner, date, payment=None):
        taxes = self.env["account.tax"]
        for rec in self:
            if rec.webservice:
                taxes += rec.sudo()._get_tax_from_ws(partner, date)
            else:
                taxes += rec.default_tax_id
        return taxes

    @api.depends("fiscal_position_id", "tax_type", "l10n_ar_is_iibb")
    def _compute_tax_template_domain(self):
        for rec in self:
            domain = rec._get_tax_domain(filter_tax_group=False)
            if not rec.l10n_ar_is_iibb:
                domain += [("l10n_ar_tax_type", "not in", ["iibb_untaxed", "iibb_total"])]
            rec.tax_template_domain = domain

    @api.model_create_multi
    def create(self, vals_list):
        """Try to resolve default_tax_id from tax_group_id + aliquot before INSERT
        (aliquot defaults to 0, i.e. the group's zero-aliquot tax) and derive webservice
        from it. If no matching tax can be resolved, default_tax_id stays unset and the
        required=True constraint raises as usual."""
        for vals in vals_list:
            if not vals.get("default_tax_id") and vals.get("tax_group_id"):
                stub = self.new(vals)
                stub._sync_default_tax_from_ux_fields()
                if stub.default_tax_id:
                    vals["default_tax_id"] = stub.default_tax_id.id
                    if stub.webservice and "webservice" not in vals:
                        vals["webservice"] = stub.webservice
            if vals.get("default_tax_id") and "webservice" not in vals:
                stub = self.new(vals)
                vals["webservice"] = stub._get_webservice_for_state(stub.default_tax_id.l10n_ar_state_id)
        return super().create(vals_list)

    @api.depends("default_tax_id")
    def _compute_tax_group_id(self):
        for rec in self:
            rec.tax_group_id = rec.default_tax_id.tax_group_id

    @api.depends("default_tax_id")
    def _compute_aliquot(self):
        for rec in self:
            rec.aliquot = rec.default_tax_id.amount

    def _inverse_tax_group_aliquot(self):
        self._sync_default_tax_from_ux_fields()

    @api.onchange("tax_group_id")
    def _onchange_tax_group_id(self):
        """Resolve default_tax_id from the group (and aliquot); selecting the group alone
        defaults to its zero-aliquot tax, so the line can be saved with just the group."""
        if self.tax_group_id:
            self._sync_default_tax_from_ux_fields()

    @api.onchange("aliquot")
    def _onchange_aliquot(self):
        """When aliquot changes (including to 0), sync if group is set."""
        if self.tax_group_id:
            self._sync_default_tax_from_ux_fields()

    def _get_webservice_for_state(self, state):
        """Returns the webservice selection value for a given state (res.country.state).
        Override in downstream modules to add support for additional jurisdictions."""
        mapping = {
            "901": "agip",  # CABA
            "902": "arba",  # Buenos Aires provincia
            "904": "rentas_cordoba",  # Córdoba
            "921": "padron",  # Santa Fe
        }
        return mapping.get(state.jurisdiction_code if state else "", False)

    def _sync_default_tax_from_ux_fields(self):
        """Derives default_tax_id (and webservice) from tax_group_id + aliquot.
        Only runs for IIBB groups; non-IIBB taxes (Ganancias, IVA, etc.) are
        selected directly by the user via default_tax_id."""
        for rec in self:
            if not rec.tax_group_id:
                continue
            if not rec.tax_group_id.tax_ids.filtered(lambda t: t.l10n_ar_state_id):
                continue
            new_tax = rec._ensure_tax(rec.aliquot)
            if new_tax and new_tax != rec.default_tax_id:
                rec.default_tax_id = new_tax
            if new_tax:
                rec.webservice = rec._get_webservice_for_state(new_tax.l10n_ar_state_id)

    @api.depends("fiscal_position_id.company_id", "tax_type")
    def _compute_tax_group_id_domain(self):
        for rec in self:
            company = rec.fiscal_position_id.company_id or rec.env.company
            # con _check_company_domain (parent_of) una sucursal puede elegir los grupos de impuestos
            # de la compañía padre, igual que el dominio de default_tax_id (_get_tax_domain)
            domain = self.env["account.tax.group"]._check_company_domain(company)
            domain += [("l10n_ar_vat_afip_code", "=", False)]
            if rec.tax_type == "perception":
                domain += [("tax_ids.type_tax_use", "=", "sale")]
            elif rec.tax_type == "withholding":
                domain += [("tax_ids.l10n_ar_withholding_payment_type", "=", "supplier")]
            rec.tax_group_id_domain = json.dumps(domain)

    def _get_tax_domain(self, filter_tax_group=True):
        self.ensure_one()
        domain = self.env["account.tax"]._check_company_domain(self.fiscal_position_id.company_id)
        domain += [("amount_type", "in", ["percent"])]
        if filter_tax_group:
            tax_group = self.tax_group_id or self.default_tax_id.tax_group_id
            if tax_group:
                domain += [("tax_group_id", "=", tax_group.id)]
            if self.tax_type == "withholding":
                # TODO esto lo deberiamos borrar al ir a odoo 19 y solo usar los tax groups
                # por ahora, para no renegar con scripts de migra que requieran crear tax groups para cada jurisdiccion y
                # ademas luego tener que ajustar a lo que hagamos en 19, usamos la jursdiccion como elemento de agrupacion
                # solo para retenciones.
                # Derivamos el estado desde tax_group_id (cuando fue cambiado) para no filtrar
                # por el estado del default_tax_id anterior (jurisdicción vieja).
                state_id = False
                if self.tax_group_id:
                    ref_tax = (
                        self.env["account.tax"]
                        .with_context(active_test=False)
                        .search(
                            [
                                ("tax_group_id", "=", self.tax_group_id.id),
                                ("l10n_ar_withholding_payment_type", "=", "supplier"),
                            ],
                            limit=1,
                        )
                    )
                    state_id = ref_tax.l10n_ar_state_id.id if ref_tax else False
                if not state_id and self.default_tax_id:
                    state_id = self.default_tax_id.l10n_ar_state_id.id
                if state_id:
                    domain += [("l10n_ar_state_id", "=", state_id)]
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
        if tax and not tax.active:
            tax.active = True
        if not tax:
            # Buscar template desde el tax_group actual (puede ser un grupo nuevo/diferente).
            # Esto garantiza que el impuesto copiado tenga el estado/jurisdicción correcta.
            template_domain = self._get_tax_domain(filter_tax_group=True)
            template_tax = self.env["account.tax"].with_context(active_test=False).search(template_domain, limit=1)
            if not template_tax:
                template_tax = self.default_tax_id
            if not template_tax:
                return self.env["account.tax"]
            if "%" not in template_tax.name:
                name = f"{template_tax.name} {rate}%"
            else:
                name = re.sub(r"\b\d+(\.\d+)?\s*%", f"{rate}%", template_tax.name)

            tax = template_tax.copy(
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
        # TODO revisar porque necesitamos esto
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

    def _search_padron_file(self, state_id, date):
        """Busca un archivo de padrón para una jurisdicción y fecha dadas
        :param state_id: ID del estado/jurisdicción
        :param date: Fecha para validar vigencia del padrón
        :return: Registro de res.company.jurisdiction.padron o recordset vacío
        """
        self.ensure_one()
        res = self.env["res.company.jurisdiction.padron"].search(
            [
                ("state_id", "in", state_id.ids),
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
        return res

    def _get_agip_data(self, partner, date, to_date):
        # si es base en data demo devolvemos una alicuota demo para que no falle la demo data
        if self.env.ref("base.user_demo", raise_if_not_found=False):
            return (2.5 if self.tax_type == "withholding" else 3.0, "VALOR DUMMY | dummy")
        raise UserError(_("Missing ADHOC credential configuration for AGIP tax rate queries"))

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

        # si es una base demo devolvemos una alicuota dummy para que no falle la demo data
        if self.env.ref("base.user_demo", raise_if_not_found=False):
            return (2.5 if self.tax_type == "withholding" else 3.0, "VALOR DUMMY | dummy")

        cuit = partner.ensure_vat()
        _logger.info("Getting ARBA data for cuit %s from date %s to date %s" % (date, to_date, cuit))

        # Si no existe padron NO devolvemos ref y pasamos a consultar alícuota al webservice
        alicuot, ref = self._get_padron_data(partner, date, to_date)
        if ref:
            return alicuot, ref

        arba_cit = self.fiscal_position_id.company_id.arba_consultar_contribuyente(cuit, date, to_date)
        if arba_cit.get("NumeroComprobante"):
            tax_data = "%s | %s | %s" % (
                arba_cit.get("NumeroComprobante"),
                arba_cit.get("CodigoHash"),
                arba_cit.get("GrupoRetencion") if self.tax_type == "withholding" else arba_cit.get("GrupoPercepcion"),
            )
            if self.tax_type == "withholding":
                return (
                    float(arba_cit.get("AlicuotaRetencion").replace(",", "."))
                    if arba_cit.get("AlicuotaRetencion")
                    else None,
                    tax_data,
                )
            else:
                return (
                    float(arba_cit.get("AlicuotaPercepcion").replace(",", "."))
                    if arba_cit.get("AlicuotaPercepcion")
                    else None,
                    tax_data,
                )
        else:
            ref = (
                self.env._("%s | CUIT %s not present on padron ARBA") % (arba_cit.get("CodigoHash"), cuit)
                if arba_cit.get("CodigoError") == "11"
                else arba_cit.get("CodigoHash")
            )
            return None, ref

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

        error_msg = _(
            "Could not get the tax rate from the rentascordoba webservice.\n\n"
            "To assign the Córdoba tax rate to a contact, follow these steps:\n"
            "1) Check the contact's tax rate at: https://www.rentascordoba.gob.ar/gestiones/consulta-alicuota\n"
            "2) Manually create the tax rate in the Contact form view (tab 'Accounting').\n\n"
            "If you have questions or the problem persists, please contact our Support team.\n"
            "Error detail:\n"
        )

        # Realizar solicitud
        try:
            r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
        except requests.exceptions.Timeout as e:
            _logger.warning("%s" % str(e))
<<<<<<< a7c128b96b63159b11ec4375da3a10d7ee9e3a32
            raise UserError(error_msg + _("Timeout error when getting data."))
||||||| ba3371a4b4c0657a34a6cafde50b664d36582a87
            raise UserError("%s" % msg)
=======
            raise UserError(error_msg + self.env._("Timeout error when getting data.")) from e
>>>>>>> 613f235a4e881e28107c60be810178001e9cf979
        except requests.exceptions.RequestException as e:
            _logger.warning("%s" % str(e))
<<<<<<< a7c128b96b63159b11ec4375da3a10d7ee9e3a32
            raise UserError(error_msg)
        if r.status_code == 404:
            raise UserError(error_msg + _("404 Not Found error."))
        json_body = r.json()
||||||| ba3371a4b4c0657a34a6cafde50b664d36582a87
            raise UserError("%s" % error_msg)
        if r.status_code == 404:
            msg = _(error_msg + "404 Not Found error.")
            raise UserError("%s" % msg)
        json_body = r.json()
=======
            raise UserError(error_msg) from e
        if not r.ok:
            _logger.warning("rentascordoba answered HTTP %s: %s", r.status_code, r.text[:500])
            raise UserError(error_msg + self.env._("HTTP %s error.") % r.status_code)
        # el webservice contesta HTML (pagina de error, mantenimiento) o un body vacio cuando esta
        # caido, y con un status que no siempre es de error: sin esta guarda el JSONDecodeError sale
        # crudo al usuario en vez del instructivo de arriba (tickets 108553, 122532, 126698)
        try:
            json_body = r.json()
        except requests.exceptions.JSONDecodeError as e:
            _logger.warning("rentascordoba answered a non-JSON body: %s", r.text[:500])
            raise UserError(error_msg + self.env._("The webservice answered a non-JSON response.")) from e
>>>>>>> 613f235a4e881e28107c60be810178001e9cf979
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
                        _("Cannot automatically get the tax rate for date %s. Please enter it manually on the contact.")
                        % date
                    )

        return aliquot, ref

    def _get_padron_data(self, partner, date, to_date):
        """Método implementado para obtener alícuota de padrón ARBA y Santa Fe:
        jurisdiction_code de Santa Fe = 921, de ARBA = 902
        1) Santa Fe:
         * si no existe padrón para el período correspondiente entonces devuelve UserError para que lo cargue.
         * si existe padrón para el período correspondiente, busca el CUIT en el padrón y:
            a) si lo encuentra devuelve la tasa y "Alícuota padrón Santa Fe",
            b) si no lo encuentra devuelve None, "Alícuota castigo. No figura en padrón Santa Fe"
        2) ARBA:
         * si no existe padrón devuelve None, None
         * si existe padrón para el período correspondiente, busca el CUIT en el padrón y:
            a) si lo encuentra devuelve la tasa y "Alícuota padrón ARBA (archivo importado)",
            b) si no lo encuentra devuelve None, "Alícuota no inscripto ARBA (archivo importado)"

        return: alicuot, ref
        """
        self.ensure_one()
        if self.env.ref("base.user_demo", raise_if_not_found=False):
            return (2.5 / 3.0, "VALOR DUMMY | dummy")
        state = self.default_tax_id.l10n_ar_state_id
        padron_file = self._search_padron_file(state, date)
        if not padron_file:
            # si la consulta de padron viene por "contingencia" (por ej. se usa ws de arba o agip) y no hay padron, no queremos raise
            if self.webservice != "padron":
                return None, None
            # Si se está consultando alícuota con tipo "padron" y no hay, entonces damos error.
            raise UserError(
                _(
                    "No padron uploaded for the indicated date %s to %s. You must upload it in 'Accounting / Configuration / AFIP / Tax Rate Padron by Company' or manually enter the tax rate on the contact for the current period."
                )
                % (date, to_date)
            )
        nro, alicuot_ret, alicuot_per = padron_file._get_aliquot(partner)
        if state.jurisdiction_code == "921":
            if nro:
                # en santa fe en realidad no hay nro, viene True/False (Segun si lo encontramos), por eso no devolvemos string genérica
                return (
                    alicuot_ret if self.tax_type == "withholding" else alicuot_per,
                    _("Santa Fe padron aliquot"),
                )
            else:
                return None, _("Penalty aliquot. Not found in Santa Fe padron")
        if state.jurisdiction_code == "902":
            if nro:
                return (
                    float(alicuot_ret.replace(",", "."))
                    if self.tax_type == "withholding"
                    else float(alicuot_per.replace(",", ".")),
                    _("ARBA padron aliquot (imported file)"),
                )
            else:
                return None, _("ARBA unregistered aliquot (imported file)")
