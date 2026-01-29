import logging
import warnings
import xml.etree.ElementTree as ET
from hashlib import md5

import requests
from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=DeprecationWarning)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _get_arba_environment_type(self):
        """
        Function to define homologation/production environment
        First it search for a paramter "arba.ws.env.type" if exists and:
        * is production --> production
        * is homologation --> homologation
        Else
        Search for 'server_mode' parameter on conf file. If that parameter is:
        * 'test' or 'develop' -->  homologation
        * other or no parameter -->  production
        """
        # como no se dispone de claves de homologacion usamos produccion
        # siempre
        environment_type = "production"
        return environment_type

    @api.model
    def get_arba_login_url(self, environment_type):
        if environment_type == "production":
            arba_login_url = "https://dfe.arba.gov.ar/DomicilioElectronico/SeguridadCliente/dfeServicioConsulta.do"
        else:
            arba_login_url = "https://dfe.test.arba.gov.ar/DomicilioElectronico/SeguridadCliente/dfeServicioConsulta.do"
        return arba_login_url

    def _arba_prepare_file(self, vat, date_from, date_to):
        qcontext = {
            "date_to": date_to,
            "date_from": date_from,
            "vats": vat if isinstance(vat, list) else [vat],
        }
        xml = str(self.env["ir.ui.view"]._render_template("l10n_ar_tax.arba_alicout_query", qcontext)).strip()
        hash_signature = md5(xml.encode()).hexdigest()
        filename = "DFEServicioConsulta_%s.xml" % hash_signature
        return (filename, str(xml).strip(), "text/xml")

    def _arba_cit_parse_response(self, response_xml):
        root = ET.fromstring(response_xml)
        if root.tag == "ERROR":
            error_type = root.find(".//tipoError").text
            error_code = root.find(".//codigoError").text
            error_msg = root.find(".//mensajeError").text.replace("<![CDATA[", "").replace("]]/>", "")
            raise UserError(_("ARBA Error %s(%s): %s") % (error_type, error_code, error_msg))
        if root.tag == "COMPROBANTE":
            try:
                alicouts = {
                    "NumeroComprobante": root.find(".//numeroComprobante").text,
                }
                # TODO Por ahora solo retornamos un contribuyente y por retrocompatibilidad
                # deberiamos a mantenerlo cantidadContribuyentes == 1
                for contribuyente in root.find(".//contribuyentes").findall("contribuyente"):
                    alicouts["AlicuotaPercepcion"] = contribuyente.find("alicuotaPercepcion").text
                    alicouts["AlicuotaRetencion"] = contribuyente.find("alicuotaRetencion").text
                    alicouts["GrupoPercepcion"] = contribuyente.find("grupoPercepcion").text
                    alicouts["GrupoRetencion"] = contribuyente.find("grupoRetencion").text
                return alicouts
            except Exception as e:
                _logger.error("Error parsing ARBA response: %s\n %s", e, str(response_xml))
                raise UserError(_("Error parsing ARBA response: %s") % str(e))
        _logger.error("Error parsing ARBA response: %s", str(response_xml))
        raise UserError(_("Error parsing ARBA response"))

    def arba_consultar_contribuyente(self, vat, date_from, date_to):
        self.ensure_one()
        self.partner_id.ensure_vat()
        if not self.arba_cit:
            raise UserError(_("You must configure CIT password on company %s") % (self.name))
        environment_type = self._get_arba_environment_type()
        file = self._arba_prepare_file(vat, date_from, date_to)
        login_url = self.get_arba_login_url(environment_type)
        arba_alicout_timeout = int(
            self.env["ir.config_parameter"].sudo().get_param("l10n_ar_tax.arba_alicout_timeout", default=40)
        )
        request_data = {
            "user": self.partner_id.ensure_vat(),
            "password": self.arba_cit,
        }
        res = requests.post(login_url, data=request_data, files={"file": file}, timeout=arba_alicout_timeout)
        if res.ok:
            response_xml = self._arba_cit_parse_response(res.content)
        else:
            _logger.error("Error parsing ARBA response: %s\n %s", str(res.text))
            raise UserError(self.env._("Error parsing ARBA response: %s") % str(res.text))
        return response_xml
