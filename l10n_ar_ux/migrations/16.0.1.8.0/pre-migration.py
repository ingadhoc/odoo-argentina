from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info('Forzando la actualizacion de data demo sobre actividades, impuestos y conceptos')

    models = ['afip.concept', 'afip.activity', 'afip.tax']
    for model in models:

        # -> buscar todos los registrods creados en odoo para mi modelo
        actividades = env[model].search([])
        # -> buscar en la tabla irmodeldata todos los registtros que sean de este modelo
        model_data = env['ir.model.data'].search([('model','=',model)])
        # -> conseguir la lista de elementos que estan desde el punto dos res.id
        activities_con_xml_id = env[model].browse(model_data.mapped('res_id'))
        # -> obtener los registros de mi modelo que no tienen aun xml_id(diferencia entre resultado de 3 y 1)
        non_xml_id_activity = actividades - activities_con_xml_id
        # -> crear un xml_id a todos los registros obtenidos en 4
        for rec in non_xml_id_activity:
            model_data.create({
                'name':  '%s_%s' % (model.replace('.', '_'), rec.code),
                'model': rec._name,
                'module': 'l10n_ar_ux',
                'res_id': rec.id,
                'noupdate': True,
            })
