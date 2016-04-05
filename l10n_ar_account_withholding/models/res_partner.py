# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.tools as tools
from pyafipws.iibb import IIBB
from pyafipws.padron import PadronAFIP
from openerp.exceptions import Warning
import logging
from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.multi
    def update_data_from_padron_afip(self):
        for partner in self:
            document_number = partner.document_number
            if not document_number or partner.document_type_id.afip_code != 80:
                raise Warning(_(
                    'No CUIT for partner %s') % (self.name))
            vals = self.get_data_from_padron_afip(document_number)
            partner.write(vals)

    @api.multi
    def get_data_from_padron_afip(self, cuit):
        # TODO agregar funcionalidad de descargar constancia, ver readme del
        # modulo
        self.ensure_one()
        padron = PadronAFIP()
        padron.Consultar(cuit)
        vals = {
            'name': padron.denominacion,
            # 'name': padron.tipo_persona,
            # 'name': padron.tipo_doc,
            # 'name': padron.dni,
            # 'name': padron.estado,
            'street': padron.direccion,
            'city': padron.localidad,
            'zip': padron.cod_postal,
            # '': padron.impuestos,
            # '': padron.actividades,
            # '': padron.imp_iva,
            # '': padron.actividad_monotributo,
            # '': padron.empleador,
            }
        if padron.provincia:
            state = self.env['res.country.state'].search([
                ('name', 'ilike', padron.provincia),
                ('country_id.code', '=', 'AR')], limit=1)
            if state:
                vals['state_id'] = state.id
        print 'vals', vals
        return vals
