# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from pyafipws.padron import PadronAFIP
from openerp.exceptions import Warning
# import os
import base64
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # campos desde
    # http://www.sistemasagiles.com.ar/trac/wiki/PadronContribuyentesAFIP
    # profits_tax_type = fields.Selection([
    estado_padron = fields.Char(
        'Estado AFIP',
    )
    imp_ganancias_padron = fields.Selection([
        ('NI', 'No Inscripto'),
        ('AC', 'Activo'),
        ('EX', 'Exento'),
        # ('NA', 'No alcanzado'),
        # ('XN', 'Exento no alcanzado'),
        # ('AN', 'Activo no alcanzado'),
        ('NC', 'No corresponde'),
    ],
        'Ganancias',
    )
    # vat_tax_type_padron = fields.Selection([
    imp_iva_padron = fields.Selection([
        ('NI', 'No Inscripto'),
        ('AC', 'Activo'),
        ('EX', 'Exento'),
        ('NA', 'No alcanzado'),
        ('XN', 'Exento no alcanzado'),
        ('AN', 'Activo no alcanzado'),
        # ('NC', 'No corresponde'),
    ],
        'IVA',
    )
    integrante_soc_padron = fields.Selection(
        [('N', 'No'), ('S', 'Si')],
        'Integrante Sociedad',
    )
    monotributo_padron = fields.Selection(
        [('N', 'No'), ('S', 'Si')],
        'Monotributo',
    )
    actividad_monotributo_padron = fields.Char(
    )
    empleador_padron = fields.Boolean(
    )
    actividades_padron = fields.Many2many(
        'afip.activity',
        'res_partner_afip_activity_rel',
        'partner_id', 'afip_activity_id',
        'Actividades',
    )
    impuestos_padron = fields.Many2many(
        'afip.tax',
        'res_partner_afip_tax_rel',
        'partner_id', 'afip_tax_id',
        'Impuestos',
    )
    last_update_padron = fields.Date(
        'Last Update Padron',
    )

    @api.multi
    def update_constancia_from_padron_afip(self):
        self.ensure_one()
        cuit = self.document_number
        if not cuit or self.document_type_id.afip_code != 80:
            raise Warning(_(
                'No CUIT for partner %s') % (self.name))
        # descarga de constancia
        # basedir = os.path.join(os.getcwd(), 'cache')
        # tmpfilename = os.path.join(basedir, "constancia.pdf")
        tmpfilename = "/tmp/constancia.pdf"
        # sie queremos mejora esto podriamos no hardecodearlo con esto
        # https://bugs.launchpad.net/openobject-addons/+bug/1040901
        padron = PadronAFIP()
        padron.Consultar(cuit)
        padron.DescargarConstancia(cuit, tmpfilename)
        f = file(tmpfilename, 'r')
        constancia = base64.b64decode(base64.encodestring(f.read()))
        f.close()
        attachments = [
            ('Constancia %s %s.pdf' % (
                self.name,
                fields.Date.context_today(self)),
                constancia)]
        self.message_post(
            subject="Constancia de inscripción actualizada",
            # subject="Actualizacion de datos desde Padron AFIP",
            # body="Datos utilizados:<br/>%s" % vals,
            attachments=attachments)

    @api.multi
    def get_data_from_padron_afip(self):

        # TODO agregar funcionalidad de descargar constancia, ver readme del
        # modulo
        self.ensure_one()
        cuit = self.document_number
        if not cuit or self.document_type_id.afip_code != 80:
            raise Warning(_(
                'No CUIT for partner %s') % (self.name))
        padron = PadronAFIP()
        padron.Consultar(cuit)

        # porque imp_iva activo puede ser S o AC
        imp_iva = padron.imp_iva
        if imp_iva == 'S':
            imp_iva = 'AC'
        elif imp_iva == 'N':
            # por ej. monotributista devuelve N
            imp_iva = 'NI'

        vals = {
            'name': padron.denominacion,
            # 'name': padron.tipo_persona,
            # 'name': padron.tipo_doc,
            # 'name': padron.dni,
            'estado_padron': padron.estado,
            'street': padron.direccion,
            'city': padron.localidad,
            'zip': padron.cod_postal,
            'actividades_padron': self.actividades_padron.search(
                [('code', 'in', padron.actividades)]).ids,
            'impuestos_padron': self.impuestos_padron.search(
                [('code', 'in', padron.impuestos)]).ids,
            'imp_iva_padron': imp_iva,
            # TODAVIA no esta funcionando
            # 'imp_ganancias_padron': padron.imp_ganancias,
            'monotributo_padron': padron.monotributo,
            'actividad_monotributo_padron': padron.actividad_monotributo,
            'empleador_padron': padron.empleador == 'S' and True,
            'integrante_soc_padron': padron.integrante_soc,
            'last_update_padron': fields.Date.today(),
        }
        ganancias_inscripto = [10, 11]
        ganancias_exento = [12]
        if set(ganancias_inscripto) & set(padron.impuestos):
            vals['imp_ganancias_padron'] = 'AC'
        elif set(ganancias_exento) & set(padron.impuestos):
            vals['imp_ganancias_padron'] = 'EX'
        elif padron.monotributo == 'S':
            vals['imp_ganancias_padron'] = 'NC'
        else:
            _logger.info(
                "We couldn't get impuesto a las ganancias from padron, you"
                "must set it manually")

        if padron.provincia:
            state = self.env['res.country.state'].search([
                ('name', 'ilike', padron.provincia),
                ('country_id.code', '=', 'AR')], limit=1)
            if state:
                vals['state_id'] = state.id
        return vals
