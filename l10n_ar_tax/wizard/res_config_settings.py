import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    @api.model
    def default_get(self, field_list=None):
        res = super().default_get(field_list)
        report = self.env.ref("l10n_ar_tax.report_payment_receipt_reversal_moves", raise_if_not_found=False)
        if report:
            res["show_reversal_moves_in_receipts"] = report.sudo().active
        return res

    arba_cit = fields.Char(
        related="company_id.arba_cit",
        readonly=False,
    )

    show_reversal_moves_in_receipts = fields.Boolean(
        compute="_compute_show_reversal_moves_in_receipts",
        inverse="_inverse_show_reversal_moves_in_receipts",
        compute_sudo=True,
    )

    def _compute_show_reversal_moves_in_receipts(self):
        for record in self:
            report = self.env.ref("l10n_ar_tax.report_payment_receipt_reversal_moves", raise_if_not_found=False)
            record.show_reversal_moves_in_receipts = report and report.sudo().active

    def _inverse_show_reversal_moves_in_receipts(self):
        report = self.env.ref("l10n_ar_tax.report_payment_receipt_reversal_moves", raise_if_not_found=False)
        if not report:
            return
        report.sudo().active = self.show_reversal_moves_in_receipts

    def l10n_ar_arba_cit_test(self):
        self.ensure_one()
        cuit = self.company_id.partner_id.ensure_vat()
        _logger.info("Getting ARBA data for cuit %s" % (cuit))
        try:
            ws = self.company_id.arba_connect()
            ws.ConsultarContribuyentes(
                fields.Date.start_of(fields.Date.today(), "month").strftime("%Y%m%d"),
                fields.Date.end_of(fields.Date.today(), "month").strftime("%Y%m%d"),
                cuit,
            )
        except Exception as exp:
            raise UserError(_("No se pudo conectar a ARBA: %s") % str(exp))

        if ws.CodigoError:
            self.company_id._process_message_error(ws)
        raise UserError(_("La conexión ha sido exitosa"))
