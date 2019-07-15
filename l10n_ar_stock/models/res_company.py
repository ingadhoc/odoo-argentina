from odoo import models, api, _
# import odoo.tools as tools
try:
    from pyafipws.cot import COT
except ImportError:
    COT = None
# from pyafipws.padron import PadronAFIP
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def get_arba_cot_login_url(self, environment_type):
        if environment_type == 'production':
            arba_login_url = (
                'https://cot.arba.gov.ar/TransporteBienes/'
                'SeguridadCliente/presentarRemitos.do')
        else:
            arba_login_url = (
                'http://cot.test.arba.gov.ar/TransporteBienes/'
                'SeguridadCliente/presentarRemitos.do')
        return arba_login_url

    @api.multi
    def arba_cot_connect(self):
        """
        Method to be called
        """
        self.ensure_one()
        cuit = self.partner_id.cuit_required()

        if not self.arba_cit:
            raise UserError(_(
                'You must configure ARBA CIT on company %s') % (
                    self.name))

        ws = COT()
        # en este caso si deberia andar cot en test y es más critico que para
        # arba donde obtenemos
        environment_type = self._get_environment_type()
        _logger.info(
            'Getting connection to ARBA on %s mode' % environment_type)

        # argumentos de conectar: self, url=None, proxy="",
        # wrapper=None, cacert=None, trace=False, testing=""
        arba_cot_url = self.get_arba_cot_login_url(environment_type)
        ws.Usuario = cuit
        ws.Password = self.arba_cit
        ws.Conectar(url=arba_cot_url)
        _logger.info(
            'Connection getted to ARBA COT with url "%s" and CUIT %s' % (
                arba_cot_url, cuit))
        return ws
