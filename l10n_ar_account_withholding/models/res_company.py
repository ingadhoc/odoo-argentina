from odoo import models, fields, api, _
# import odoo.tools as tools
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    from pyafipws.iibb import IIBB
except ImportError:
    IIBB = None
# from pyafipws.padron import PadronAFIP
from odoo.exceptions import UserError, RedirectWarning
import logging
import json
import requests
# from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    regimenes_ganancias_ids = fields.Many2many(
        'afip.tabla_ganancias.alicuotasymontos',
        'res_company_tabla_ganancias_rel',
        'company_id', 'regimen_id',
        'Regimenes Ganancia',
    )
    agip_padron_type = fields.Selection([
        ('regimenes_generales', 'Regímenes Generales')],
        string='Padron AGIP',
        default='regimenes_generales',
    )
    agip_alicuota_no_sincripto_retencion = fields.Float(
        'Agip: Alicuota no inscripto retención',
    )
    agip_alicuota_no_sincripto_percepcion = fields.Float(
        'Agip: Alicuota no inscripto percepción',
    )
    arba_alicuota_no_sincripto_retencion = fields.Float(
        'Arba: Alicuota no inscripto retención',
    )
    arba_alicuota_no_sincripto_percepcion = fields.Float(
        'Arba: Alicuota no inscripto percepción',
    )
    cdba_alicuota_no_sincripto_retencion = fields.Float(
        'Rentas Córdoba: Alícuota no inscripto retención'
    )
    cdba_alicuota_no_sincripto_percepcion = fields.Float(
        'Rentas Córdoba: Alícuota no inscripto percepción'
    )

    def _localization_use_withholdings(self):
        """ Argentinian localization use documents """
        self.ensure_one()
        return True if self.country_id == self.env.ref('base.ar') else super()._localization_use_withholdings()

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
        environment_type = 'production'
        # parameter_env_type = self.env[
        #     'ir.config_parameter'].sudo().get_param('arba.ws.env.type')
        # if parameter_env_type == 'production':
        #     environment_type = 'production'
        # elif parameter_env_type == 'homologation':
        #     environment_type = 'homologation'
        # else:
        #     server_mode = tools.config.get('server_mode')
        #     if not server_mode or server_mode == 'production':
        #         environment_type = 'production'
        #     else:
        #         environment_type = 'homologation'
        # _logger.info(
        #     'Running arba WS on %s mode' % environment_type)
        return environment_type

    @api.model
    def get_arba_login_url(self, environment_type):
        if environment_type == 'production':
            arba_login_url = (
                'https://dfe.arba.gov.ar/DomicilioElectronico/'
                'SeguridadCliente/dfeServicioConsulta.do')
        else:
            arba_login_url = (
                'https://dfe.test.arba.gov.ar/DomicilioElectronico'
                '/SeguridadCliente/dfeServicioConsulta.do')
        return arba_login_url

    def arba_connect(self):
        """
        Method to be called
        """
        self.ensure_one()
        cuit = self.partner_id.ensure_vat()

        if not self.arba_cit:
            raise UserError(_(
                'You must configure CIT password on company %s') % (self.name))

        try:
            ws = IIBB()
            environment_type = self._get_arba_environment_type()
            _logger.info(
                'Getting connection to ARBA on %s mode' % environment_type)

            # argumentos de conectar: self, url=None, proxy="",
            # wrapper=None, cacert=None, trace=False, testing=""
            arba_url = self.get_arba_login_url(environment_type)
            ws.Usuario = cuit
            ws.Password = self.arba_cit
            ws.Conectar(url=arba_url)
            _logger.info(
                'Connection getted to ARBA with url "%s" and CUIT %s' % (
                    arba_url, cuit))
        except ConnectionRefusedError:
            raise UserError('No se pudo conectar a ARBA para extraer los datos de percepcion/retención.'
                            ' Por favor espere unos minutos e intente de nuevo. Sino, cargue manualmente'
                            ' los datos en el cliente para poder operar (fecha %s)' % self.env.context.get('invoice_date'))

        return ws

    def get_agip_data(self, partner, date):
        raise UserError(_(
            'Falta configuración de credenciales de ADHOC para consulta de '
            'Alícuotas de AGIP'))

    def get_arba_data(self, partner, from_date, to_date):
        self.ensure_one()

        cuit = partner.ensure_vat()

        _logger.info(
            'Getting ARBA data for cuit %s from date %s to date %s' % (
                from_date, to_date, cuit))
        ws = self.arba_connect()
        ws.ConsultarContribuyentes(
            from_date.strftime('%Y%m%d'),
            to_date.strftime('%Y%m%d'),
            cuit)

        error = False
        msg = False
        if ws.Excepcion:
            error = True
            msg = str((ws.Traceback, ws.Excepcion))
            _logger.error('Padron ARBA: Excepcion %s' % msg)

        # ' Hubo error general de ARBA?
        if ws.CodigoError:
            if ws.CodigoError == '11':
                # we still create the record so we don need to check it again
                # on same period
                _logger.info('CUIT %s not present on padron ARBA' % cuit)
            elif ws.CodigoError == '6':
                error = True
                msg = "%s\n Error %s: %s" % (ws.MensajeError, ws.TipoError, ws.CodigoError)
                _logger.error('Padron ARBA: %s' % msg)
            else:
                self._process_message_error(ws)

        if error:
            action = self.env.ref('l10n_ar_account_withholding.act_company_jurisdiction_padron')
            raise RedirectWarning(_(
                "Obtuvimos un error al consultar el Padron ARBA.\n  %s\n\n"
                "Tiene las siguientes opciones:\n  1) Intentar nuevamente más tarde\n"
                "  2) Cargar la alícuota manualmente en el partner en cuestión\n"
                "  3) Subir el archivo del padrón utilizando el asistente de Carga de Padrones") % msg,
                action.id, _('Ir a Carga de Padrones'))

        # no ponemos esto, si no viene alicuota es porque es cero entonces
        # if not ws.AlicuotaRetencion or not ws.AlicuotaPercepcion:
        #     raise UserError('No pudimos obtener la AlicuotaRetencion')

        # ' Datos generales de la respuesta:'
        data = {
            'numero_comprobante': ws.NumeroComprobante,
            'codigo_hash': ws.CodigoHash,
            # 'CuitContribuyente': ws.CuitContribuyente,
            'alicuota_percepcion': ws.AlicuotaPercepcion and float(
                ws.AlicuotaPercepcion.replace(',', '.')),
            'alicuota_retencion': ws.AlicuotaRetencion and float(
                ws.AlicuotaRetencion.replace(',', '.')),
            'grupo_percepcion': ws.GrupoPercepcion,
            'grupo_retencion': ws.GrupoRetencion,
        }
        _logger.info('We get the following data: \n%s' % data)
        return data

    def get_cordoba_data(self, partner, date):
        """ Obtener alícuotas desde app.rentascordoba.gob.ar
        :param partner: El partner sobre el cual trabajamos
        :param date: La fecha del comprobante
        :param from_date: Fecha de inicio de validez de alícuota por defecto
        :param to_date: Fecha de fin de validez de alícuota por defecto
        Devuelve diccionario de datos
        """
        _logger.info('Getting withholding data from rentascordoba.gob.ar')
        date_date = fields.Date.from_string(date)

        # Establecer parámetros de solicitud
        url = "https://app.rentascordoba.gob.ar/rentas/rest/svcGetAlicuotas"
        payload = {'body': partner.vat}
        headers = {'content-type': 'application/json'}

        # Realizar solicitud
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        json_body = r.json()

        if r.status_code != 200:
            raise UserError('Error al contactar rentascordoba.gob.ar. '
                            'El servidor respondió: \n\n%s' % json_body)

        code = json_body.get("errorCod")

        # Capturar Códigos de Error.
        # 3 => No Inscripto, 2 => No pasible, 1 => CUIT incorrecta, 0 => OK
        if code == 3:
            alicuota_percepcion = self.cdba_alicuota_no_sincripto_percepcion
            alicuota_retencion = self.cdba_alicuota_no_sincripto_retencion
        elif code == 2:
            alicuota_percepcion = 0.0
            alicuota_retencion = 0.0
        elif code != 0:
            raise UserError(json_body.get("message"))
        else:
            dict_alic = json_body.get("sdtConsultaAlicuotas")
            alicuota_percepcion = float(dict_alic.get("CRD_ALICUOTA_PER"))
            alicuota_retencion = float(dict_alic.get("CRD_ALICUOTA_RET"))
            # Verificamos si el par_cod no es para los recien inscriptos, que vienen con fecha "0000-00-00"
            if dict_alic.get("CRD_PAR_CODIGO") != 'NUE_INS':
                # Verificar que el comprobante tenga fecha dentro de la vigencia
                from_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_INICIO"))
                to_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_FIN"))
                if not (from_date_date <= date_date <= to_date_date):
                    raise UserError(
                        'No se puede obtener automáticamente la alicuota para la '
                        'fecha %s. Por favor, ingrese la misma manualmente '
                        'en el partner.' % date)
        data = {
            'alicuota_percepcion': alicuota_percepcion,
            'alicuota_retencion': alicuota_retencion,
        }

        _logger.info("We've got the following data: \n%s" % data)

        return data

    @api.model
    def _process_message_error(self, ws):
        message = ws.MensajeError
        message = message.replace('<![CDATA[', '').replace(']]/>','')
        raise UserError(_('Padron ARBA: %s - %s (%s)') % (ws.CodigoError, message, ws.TipoError))
