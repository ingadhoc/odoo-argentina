from odoo import models, fields, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

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

    def l10n_ar_arba_cit_test(self):
        self.ensure_one()
        cuit = self.company_id.partner_id.ensure_vat()
        _logger.info('Getting ARBA data for cuit %s' % (cuit))
        try:
            ws = self.company_id.arba_connect()
            ws.ConsultarContribuyentes(
                fields.Date.start_of(fields.Date.today(), 'month').strftime('%Y%m%d'),
                fields.Date.end_of(fields.Date.today(), 'month').strftime('%Y%m%d'),
                cuit)
        except Exception as exp:
            raise UserError(_('No se pudo conectar a ARBA: %s') % str(exp))

        if ws.CodigoError:
            self.company_id._process_message_error(ws)
        raise UserError(_('La conexión ha sido exitosa'))
