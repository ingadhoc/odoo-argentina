import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    arba_cit = fields.Char(
        related="company_id.arba_cit",
        readonly=False,
    )

    def l10n_ar_arba_cit_test(self):
        self.ensure_one()
        cuit = self.company_id.partner_id.ensure_vat()
        _logger.info("Getting ARBA data for cuit %s" % (cuit))
        try:
            self.company_id.arba_consultar_contribuyente(
                cuit,
                fields.Date.start_of(fields.Date.today(), "month"),
                fields.Date.end_of(fields.Date.today(), "month"),
            )
        except Exception as exp:
            raise UserError(_("No se pudo conectar a ARBA: %s") % str(exp))

        raise UserError(_("La conexión ha sido exitosa"))
