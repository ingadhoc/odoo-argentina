from odoo import models, fields
# from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    arba_cit = fields.Char(
        related='company_id.arba_cit',
        readonly=False,
    )
    regimenes_ganancias_ids = fields.Many2many(
        related='company_id.regimenes_ganancias_ids',
        readonly=False,
    )
    agip_padron_type = fields.Selection(
        related='company_id.agip_padron_type',
        readonly=False,
    )
    agip_alicuota_no_sincripto_retencion = fields.Float(
        related='company_id.agip_alicuota_no_sincripto_retencion',
        readonly=False,
    )
    agip_alicuota_no_sincripto_percepcion = fields.Float(
        related='company_id.agip_alicuota_no_sincripto_percepcion',
        readonly=False,
    )
    arba_alicuota_no_sincripto_retencion = fields.Float(
        related='company_id.arba_alicuota_no_sincripto_retencion',
        readonly=False,
    )
    arba_alicuota_no_sincripto_percepcion = fields.Float(
        related='company_id.arba_alicuota_no_sincripto_percepcion',
        readonly=False,
    )
    cdba_alicuota_no_sincripto_retencion = fields.Float(
        related='company_id.cdba_alicuota_no_sincripto_retencion',
        readonly=False,
    )
    cdba_alicuota_no_sincripto_percepcion = fields.Float(
        related='company_id.cdba_alicuota_no_sincripto_percepcion',
        readonly=False,
    )
    group_partner_tax_withholding_amount_type = fields.Boolean(
        'Allow to choose base amount type for withholdings on partners',
        implied_group='l10n_ar_account_withholding.partner_tax_withholding_amount_type',
    )
