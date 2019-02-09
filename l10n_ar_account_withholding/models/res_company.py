from odoo import models, fields, api, _
# import odoo.tools as tools
try:
    from pyafipws.iibb import IIBB
except ImportError:
    IIBB = None
# from pyafipws.padron import PadronAFIP
from odoo.exceptions import UserError
import logging
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

    @api.multi
    def arba_connect(self):
        """
        Method to be called
        """
        self.ensure_one()
        cuit = self.partner_id.cuit_required()

        if not self.arba_cit:
            raise UserError(_(
                'You must configure ARBA CIT on company %s') % (
                    self.name))

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
        return ws

    def get_agip_data(self, partner, date):
        raise UserError(_(
            'Falta configuración de credenciales de ADHOC para consulta de '
            'Alícuotas de AGIP'))

    def get_arba_data(self, partner, from_date, to_date):
        self.ensure_one()

        # from_date = date + relativedelta(day=1).strftime('%Y%m%d')
        # to_date = date + relativedelta(
        #     day=1, days=-1, months=+1).strftime('%Y%m%d')

        cuit = partner.cuit_required()

        _logger.info(
            'Getting ARBA data for cuit %s from date %s to date %s' % (
                from_date, to_date, cuit))
        ws = self.arba_connect()
        ws.ConsultarContribuyentes(
            from_date,
            to_date,
            cuit)

        if ws.Excepcion:
            raise UserError("%s\nExcepcion: %s" % (
                ws.Traceback, ws.Excepcion))

        # ' Hubo error general de ARBA?
        if ws.CodigoError:
            if ws.CodigoError == '11':
                # we still create the record so we don need to check it again
                # on same period
                _logger.info('CUIT %s not present on padron ARBA' % cuit)
            else:
                raise UserError("%s\nError %s: %s" % (
                    ws.MensajeError, ws.TipoError, ws.CodigoError))

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
            'from_date': from_date,
            'to_date': to_date,
        }
        _logger.info('We get the following data: \n%s' % data)
        return data
