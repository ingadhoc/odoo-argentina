from odoo import models, fields
import logging
# from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # TODO renombrar campo
    arba_alicuot_ids = fields.One2many(
        'res.partner.arba_alicuot',
        'partner_id',
        'Alícuotas PERC-RET',
    )
    drei = fields.Selection([
        ('activo', 'Activo'),
        ('no_activo', 'No Activo'),
    ],
        string='DREI',
    )
    # TODO agregarlo en mig a v10 ya que fix dbs no es capaz de arreglarlo
    # porque da el error antes de empezar a arreglar
    # drei_number = fields.Char(
    # )
    default_regimen_ganancias_id = fields.Many2one(
        'afip.tabla_ganancias.alicuotasymontos',
        'Regimen Ganancias por Defecto',
    )


class ResPartnerArbaAlicuot(models.Model):
    # TODO rename model to res.partner.tax or similar
    _name = "res.partner.arba_alicuot"
    _description = "res.partner.arba_alicuot"
    _order = "to_date desc, from_date desc, tag_id, company_id"

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
    )
    tag_id = fields.Many2one(
        'account.account.tag',
        domain=[('applicability', '=', 'taxes')],
        required=True,
        change_default=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.company,
    )
    from_date = fields.Date(
    )
    to_date = fields.Date(
    )
    numero_comprobante = fields.Char(
    )
    codigo_hash = fields.Char(
    )
    alicuota_percepcion = fields.Float(
    )
    alicuota_retencion = fields.Float(
    )
    grupo_percepcion = fields.Char(
    )
    grupo_retencion = fields.Char(
    )
    withholding_amount_type = fields.Selection([
        ('untaxed_amount', 'Untaxed Amount'),
        ('total_amount', 'Total Amount'),
    ],
        'Base para retenciones',
        help='Base amount used to get withholding amount',
    )
    regimen_percepcion = fields.Char(
        size=3,
        help="Utilizado para la generación del TXT para SIRCAR.\n"
        "Tipo de Régimen de Percepción (código correspondiente según "
        "tabla definida por la jurisdicción)"
    )
    regimen_retencion = fields.Char(
        size=3,
        help="Utilizado para la generación del TXT para SIRCAR.\n"
        "Tipo de Régimen de Retención (código correspondiente según "
        "tabla definida por la jurisdicción)"
    )
    api_codigo_articulo_retencion = fields.Selection([
        ('001', '001: Art.1 - inciso A - (Res. Gral. 15/97 y Modif.)'),
        ('002', '002: Art.1 - inciso B - (Res. Gral. 15/97 y Modif.)'),
        ('003', '003: Art.1 - inciso C - (Res. Gral. 15/97 y Modif.)'),
        ('004', '004: Art.1 - inciso D pto.1 - (Res. Gral. 15/97 y Modif.)'),
        ('005', '005: Art.1 - inciso D pto.2 - (Res. Gral. 15/97 y Modif.)'),
        ('006', '006: Art.1 - inciso D pto.3 - (Res. Gral. 15/97 y Modif.)'),
        ('007', '007: Art.1 - inciso E - (Res. Gral. 15/97 y Modif.)'),
        ('008', '008: Art.1 - inciso F - (Res. Gral. 15/97 y Modif.)'),
        ('009', '009: Art.1 - inciso H - (Res. Gral. 15/97 y Modif.)'),
        ('010', '010: Art.1 - inciso I - (Res. Gral. 15/97 y Modif.)'),
        ('011', '011: Art.1 - inciso J - (Res. Gral. 15/97 y Modif.)'),
        ('012', '012: Art.1 - inciso K - (Res. Gral. 15/97 y Modif.)'),
        ('013', '013: Art.1 - inciso L - (Res. Gral. 15/97 y Modif.)'),
        ('014', '014: Art.1 - inciso LL pto.1 - (Res. Gral. 15/97 y Modif.)'),
        ('015', '015: Art.1 - inciso LL pto.2 - (Res. Gral. 15/97 y Modif.)'),
        ('016', '016: Art.1 - inciso LL pto.3 - (Res. Gral. 15/97 y Modif.)'),
        ('017', '017: Art.1 - inciso LL pto.4 - (Res. Gral. 15/97 y Modif.)'),
        ('018', '018: Art.1 - inciso LL pto.5 - (Res. Gral. 15/97 y Modif.)'),
        ('019', '019: Art.1 - inciso M - (Res. Gral. 15/97 y Modif.)'),
        ('020', '020: Art.2 - (Res. Gral. 15/97 y Modif.)'),
    ],
        string='Código de Artículo/Inciso por el que retiene',
    )
    api_codigo_articulo_percepcion = fields.Selection([
        ('021', '021: Art.10 - inciso A - (Res. Gral. 15/97 y Modif.)'),
        ('022', '022: Art.10 - inciso B - (Res. Gral. 15/97 y Modif.)'),
        ('023', '023: Art.10 - inciso D - (Res. Gral. 15/97 y Modif.)'),
        ('024', '024: Art.10 - inciso E - (Res. Gral. 15/97 y Modif.)'),
        ('025', '025: Art.10 - inciso F - (Res. Gral. 15/97 y Modif.)'),
        ('026', '026: Art.10 - inciso G - (Res. Gral. 15/97 y Modif.)'),
        ('027', '027: Art.10 - inciso H - (Res. Gral. 15/97 y Modif.)'),
        ('028', '028: Art.10 - inciso I - (Res. Gral. 15/97 y Modif.)'),
        ('029', '029: Art.10 - inciso J - (Res. Gral. 15/97 y Modif.)'),
        ('030', '030: Art.11 - (Res. Gral. 15/97 y Modif.)'),
    ],
        string='Código de artículo Inciso por el que percibe',
    )
    api_articulo_inciso_calculo_selection = [
        ('001', '001: Art. 5º 1er. párrafo (Res. Gral. 15/97 y Modif.)'),
        ('002', '002: Art. 5º inciso 1)(Res. Gral. 15/97 y Modif.)'),
        ('003', '003: Art. 5° inciso 2)(Res. Gral. 15/97 y Modif.)'),
        ('004', '004: Art. 5º inciso 4)(Res. Gral. 15/97 y Modif.)'),
        ('005', '005: Art. 5° inciso 5)(Res. Gral. 15/97 y Modif.)'),
        ('006', '006: Art. 6º inciso a)(Res. Gral. 15/97 y Modif.)'),
        ('007', '007: Art. 6º inciso b)(Res. Gral. 15/97 y Modif.)'),
        ('008', '008: Art. 6º inciso c)(Res. Gral. 15/97 y Modif.)'),
        ('009', '009: Art. 12º)(Res. Gral. 15/97 y Modif.)'),
        ('010', '010: Art. 6º inciso d)(Res. Gral. 15/97 y Modif.)'),
        ('011', '011: Art. 5° inciso 6)(Res. Gral. 15/97 y Modif.)'),
        ('012', '012: Art. 5° inciso 3)(Res. Gral. 15/97 y Modif.)'),
        ('013', '013: Art. 5° inciso 7)(Res. Gral. 15/97 y Modif.)'),
        ('014', '014: Art. 5° inciso 8)(Res. Gral. 15/97 y Modif.)'),
    ]
    api_articulo_inciso_calculo_percepcion = fields.Selection(
        api_articulo_inciso_calculo_selection,
        string='Artículo/Inciso para el cálculo percepción',
    )
    api_articulo_inciso_calculo_retencion = fields.Selection(
        api_articulo_inciso_calculo_selection,
        string='Artículo/Inciso para el cálculo retención',
    )
