##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError
try:
    from pysimplesoap.client import SoapFault
except ImportError:
    SoapFault = None
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    gross_income_number = fields.Char(
        'Gross Income Number',
        size=64,
    )
    gross_income_type = fields.Selection([
        ('multilateral', 'Multilateral'),
        ('local', 'Local'),
        ('no_liquida', 'No Liquida'),
    ],
        'Gross Income Type',
    )
    gross_income_jurisdiction_ids = fields.Many2many(
        'res.country.state',
        string='Gross Income Jurisdictions',
        help='The state of the company is cosidered the main jurisdiction',
    )
    start_date = fields.Date(
        'Start-up Date',
    )
    afip_responsability_type_id = fields.Many2one(
        'afip.responsability.type',
        'AFIP Responsability Type',
        auto_join=True,
        index=True,
    )
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
        # TODO implementar, al 30.11.2017 solo ws_sr_padron_a4 esta
        # implementado
        return True
        # # DESACTIVAMOS ESTO HASTA ARREGLARLO
        # cuit = self.cuit
        # # cuit = self.cuit_required

        # # descarga de constancia
        # # basedir = os.path.join(os.getcwd(), 'cache')
        # # tmpfilename = os.path.join(basedir, "constancia.pdf")
        # tmpfilename = "/tmp/constancia.pdf"
        # # sie queremos mejora esto podriamos no hardecodearlo con esto
        # # https://bugs.launchpad.net/openobject-addons/+bug/1040901
        # padron = self.env.user.company_id.get_connection(
        #     'ws_sr_padron_a5').connect()
        # padron.DescargarConstancia(cuit, tmpfilename)
        # f = file(tmpfilename, 'r')
        # constancia = base64.b64decode(base64.encodestring(f.read()))
        # f.close()
        # attachments = [
        #     ('Constancia %s %s.pdf' % (
        #         self.name,
        #         fields.Date.context_today(self)),
        #         constancia)]
        # self.message_post(
        #     subject="Constancia de inscripción actualizada",
        #     # subject="Actualizacion de datos desde Padron AFIP",
        #     # body="Datos utilizados:<br/>%s" % vals,
        #     attachments=attachments)

    @api.multi
    def get_data_from_padron_afip(self):
        self.ensure_one()
        cuit = self.cuit_required()

        # GET COMPANY
        # if there is certificate for user company, use that one, if not
        # use the company for the first certificate found
        company = self.env.user.company_id
        env_type = company._get_environment_type()
        try:
            certificate = company.get_key_and_certificate(
                company._get_environment_type())
        except Exception:
            certificate = self.env['afipws.certificate'].search([
                ('alias_id.type', '=', env_type),
                ('state', '=', 'confirmed'),
            ], limit=1)
            if not certificate:
                raise UserError(_(
                    'Not confirmed certificate found on database'))
            company = certificate.alias_id.company_id

        # consultamos a5 ya que extiende a4 y tiene validez de constancia
        # padron = company.get_connection('ws_sr_padron_a4').connect()
        padron = company.get_connection('ws_sr_padron_a5').connect()
        error_msg = _(
            'No pudimos actualizar desde padron afip al partner %s (%s).\n'
            'Recomendamos verificar manualmente en la página de AFIP.\n'
            'Obtuvimos este error: %s')
        try:
            padron.Consultar(cuit)
        except SoapFault as e:
            raise UserError(error_msg % (self.name, cuit, e.faultstring))
        except Exception as e:
            raise UserError(error_msg % (self.name, cuit, e))

        if not padron.denominacion or padron.denominacion == ', ':
            raise UserError(error_msg % (
                self.name, cuit, 'La afip no devolvió nombre'))

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
            # depending on the database, caba can have one of this codes
            caba_codes = ['C', 'CABA', 'ABA']
            # if not localidad then it should be CABA.
            if not padron.localidad:
                state = self.env['res.country.state'].search([
                    ('code', 'in', caba_codes),
                    ('country_id.code', '=', 'AR')], limit=1)
            # If localidad cant be caba
            else:
                state = self.env['res.country.state'].search([
                    ('name', 'ilike', padron.provincia),
                    ('code', 'not in', caba_codes),
                    ('country_id.code', '=', 'AR')], limit=1)
            if state:
                vals['state_id'] = state.id

        if imp_iva == 'NI' and padron.monotributo == 'S':
            vals['afip_responsability_type_id'] = self.env.ref(
                'l10n_ar_account.res_RM').id
        elif imp_iva == 'AC':
            vals['afip_responsability_type_id'] = self.env.ref(
                'l10n_ar_account.res_IVARI').id
        elif imp_iva == 'EX':
            vals['afip_responsability_type_id'] = self.env.ref(
                'l10n_ar_account.res_IVAE').id
        else:
            _logger.info(
                "We couldn't infer the AFIP responsability from padron, you"
                "must set it manually.")

        return vals

    @api.multi
    @api.constrains('gross_income_jurisdiction_ids', 'state_id')
    def check_gross_income_jurisdictions(self):
        for rec in self:
            if rec.state_id and \
                    rec.state_id in rec.gross_income_jurisdiction_ids:
                raise UserError(_(
                    'Jurisdiction %s is considered the main jurisdiction '
                    'because it is the state of the company, please remove it'
                    'from the jurisdiction list') % rec.state_id.name)
