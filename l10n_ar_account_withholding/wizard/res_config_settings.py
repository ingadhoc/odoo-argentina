from odoo import models, fields
# from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    regimenes_ganancias_ids = fields.Many2many(
        related='company_id.regimenes_ganancias_ids'
    )
    agip_padron_type = fields.Selection(
        related='company_id.agip_padron_type'
    )
    agip_alicuota_no_sincripto_retencion = fields.Float(
        related='company_id.agip_alicuota_no_sincripto_retencion'
    )
    agip_alicuota_no_sincripto_percepcion = fields.Float(
        related='company_id.agip_alicuota_no_sincripto_percepcion'
    )
    arba_alicuota_no_sincripto_retencion = fields.Float(
        related='company_id.arba_alicuota_no_sincripto_retencion'
    )
    arba_alicuota_no_sincripto_percepcion = fields.Float(
        related='company_id.arba_alicuota_no_sincripto_percepcion'
    )
    group_partner_tax_withholding_amount_type = fields.Boolean(
        'Allow to choose base amount type for withholdings on partners',
        implied_group=\
            'l10n_ar_account_withholding.partner_tax_withholding_amount_type',
    )
