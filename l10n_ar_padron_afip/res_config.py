# -*- coding: utf-8 -*-
from openerp import models, api, _
from pyafipws.padron import PadronAFIP
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class argentinian_base_configuration(models.TransientModel):
    _inherit = 'argentinian.base.config.settings'

    @api.multi
    def refresh_taxes_from_padron(self):
        self.refresh_from_padron("impuestos")

    @api.multi
    def refresh_concepts_from_padron(self):
        self.refresh_from_padron("conceptos")

    @api.multi
    def refresh_activities_from_padron(self):
        self.refresh_from_padron("actividades")

    @api.multi
    def refresh_from_padron(self, resource_type):
        """
        resource_type puede ser "impuestos", "conceptos", "actividades",
        "caracterizaciones", "categoriasMonotributo", "categoriasAutonomo".
        """
        self.ensure_one()
        if resource_type == 'impuestos':
            model = 'afip.tax'
        elif resource_type == 'actividades':
            model = 'afip.activity'
        elif resource_type == 'conceptos':
            model = 'afip.concept'
        else:
            raise Warning(_('Resource Type %s not implemented!') % (
                resource_type))
        padron = PadronAFIP()
        separator = ';'
        data = padron.ObtenerTablaParametros(resource_type, separator)
        codes = []
        for line in data:
            False, code, name, False = line.split(separator)
            vals = {
                'code': code,
                'name': name,
                'active': True,
            }
            record = self.env[model].search([('code', '=', code)], limit=1)
            codes.append(code)
            if record:
                record.write(vals)
            else:
                record.create(vals)
        # deactivate the ones that are not in afip
        self.env[model].search([('code', 'not in', codes)]).write(
            {'active': False})
