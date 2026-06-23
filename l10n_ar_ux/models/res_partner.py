import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Override to add tracking
    l10n_ar_afip_responsibility_type_id = fields.Many2one(tracking=True)

    gross_income_jurisdiction_ids = fields.Many2many(
        "res.country.state",
        string="Gross Income Jurisdictions",
        help="The state of the company is cosidered the main jurisdiction",
    )

    # ARCA Padron
    start_date = fields.Date("Activities Start")
    estado_padron = fields.Char("Estado ARCA")
    imp_ganancias_padron = fields.Selection(
        [("NI", "No Inscripto"), ("AC", "Activo"), ("EX", "Exento"), ("NC", "No corresponde")], "Ganancias"
    )
    imp_iva_padron = fields.Selection(
        [
            ("NI", "No Inscripto"),
            ("AC", "Activo"),
            ("EX", "Exento"),
            ("NA", "No alcanzado"),
            ("XN", "Exento no alcanzado"),
            ("AN", "Activo no alcanzado"),
        ],
        "IVA",
    )
    integrante_soc_padron = fields.Selection([("N", "No"), ("S", "Si")], "Integrante Sociedad")
    monotributo_padron = fields.Selection([("N", "No"), ("S", "Si")], "Monotributo")
    actividad_monotributo_padron = fields.Char()
    empleador_padron = fields.Boolean()
    impuestos_padron = fields.Many2many(
        "afip.tax", "res_partner_afip_tax_rel", "partner_id", "afip_tax_id", "Impuestos"
    )
    last_update_padron = fields.Date()

    @api.constrains("gross_income_jurisdiction_ids", "state_id")
    def check_gross_income_jurisdictions(self):
        for rec in self:
            if rec.state_id and rec.state_id in rec.gross_income_jurisdiction_ids:
                raise ValidationError(
                    _(
                        "Jurisdiction %s is considered the main jurisdiction "
                        "because it is the state of the company, please remove it "
                        "from the jurisdiction list"
                    )
                    % rec.state_id.name
                )

    @api.model
    def try_write_commercial(self, data):
        """User for website. capture the validation errors and return them.
        return (error, error_message) = (dict[fields], list(str()))"""
        error = dict()
        error_message = []
        vat = data.get("vat")
        l10n_latam_identification_type_id = data.get("l10n_latam_identification_type_id")
        l10n_ar_afip_responsibility_type_id = data.get("l10n_ar_afip_responsibility_type_id", False)

        if vat and l10n_latam_identification_type_id:
            commercial_partner = request.env.user.partner_id.commercial_partner_id
            try:
                values = {
                    "vat": vat,
                    "l10n_latam_identification_type_id": int(l10n_latam_identification_type_id),
                    "l10n_ar_afip_responsibility_type_id": int(l10n_ar_afip_responsibility_type_id)
                    if l10n_ar_afip_responsibility_type_id
                    else False,
                }
                commercial_fields = ["vat", "l10n_latam_identification_type_id", "l10n_ar_afip_responsibility_type_id"]
                values = commercial_partner.remove_readonly_required_fields(commercial_fields, values)
                with self.env.cr.savepoint():
                    commercial_partner.write(values)
            except Exception as exception_error:
                _logger.error(exception_error)
                error["vat"] = "error"
                error["l10n_latam_identification_type_id"] = "error"
                error_message.append(_(exception_error))
        return error, error_message

    def remove_readonly_required_fields(self, required_fields, values):
        """In some cases we have information showed to the user in the for that is required but that is already set
        and readonly. We do not really update this fields and then here we are trying to write them: the problem is
        that this fields has a constraint if we are trying to re-write them (even when is the same value).

        This method remove this (field, values) for the values to write in order to do avoid the constraint and not
        re-writted again when they has been already writted.

        param: @required_fields: (list) fields of the fields that we want to check
        param: @values (dict) the values of the web form

        return: the same values to write and they do not include required/readonly fields.
        """
        self.ensure_one()
        for r_field in required_fields:
            value = values.get(r_field)
            if r_field.endswith("_id"):
                if self[r_field].id == value:
                    values.pop(r_field, False)
            else:
                if self[r_field] == value:
                    values.pop(r_field, False)
        return values

    def _get_id_number_sanitize(self):
        """Devuelve los dígitos del número de identificación (0 si no hay VAT).

        Sobreescribimos el método del base ``l10n_ar`` por dos motivos:

        1. Usamos una regex en lugar de ``int(stdnum.ar.cuit.compact(vat))``:
           ``compact`` no limpia caracteres ocultos (p. ej. un word joiner
           pegado desde Excel/PDF), así que el ``int()`` reventaba al guardar un
           CUIL —que no es ``is_vat`` y por eso pasa por
           ``_run_check_identification`` (el método que invoca esto)—.

        2. Sólo sanitizamos documentos numéricos argentinos —CUIT/CUIL/DNI, los
           únicos para los que ``_get_validation_module`` devuelve un módulo—.
           El base sanitiza el VAT de *cualquier* partner argentino, borrándole
           las letras a documentos que sí pueden tenerlas (pasaporte AFIP 94,
           SIGD 99, documentos extranjeros, etc.) y corrompiendo el dato. Para
           esos devolvemos 0 (falsy) y el caller ``_run_check_identification`` no
           reescribe el VAT.

        TODO: eliminar este override cuando Odoo resuelva el bug del base
        (regresión 18.0 -> 19.0): https://github.com/odoo/odoo/issues/272173

        Mantenemos el comportamiento del base: con VAT sin dígitos devuelve un
        string vacío (los callers ya lo tratan como falsy).
        """
        self.ensure_one()
        if not self.vat or not self._get_validation_module():
            return 0
        id_number = re.sub("[^0-9]", "", self.vat)
        return id_number and int(id_number)
