from odoo import models, fields, api
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
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.user.company_id,
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
