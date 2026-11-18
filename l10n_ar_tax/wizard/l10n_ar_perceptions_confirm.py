##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.http import request


class L10nArPerceptionsConfirm(models.TransientModel):
    """Pide confirmación antes de validar documentos de venta cuyas percepciones podrían estar incompletas (ver
    ``account.fiscal.position._l10n_ar_check_perceptions``)."""

    _name = "l10n_ar.perceptions.confirm"
    _description = "Confirm perceptions"

    message = fields.Text(readonly=True)
    res_model = fields.Char(required=True)
    res_ids = fields.Json(required=True)
    method = fields.Char(required=True)

    @api.model
    def _is_button_call(self):
        """Only buttons of the web client get the wizard: code callers (automatic invoicing, portal payment) must
        keep their usual result."""
        return bool(request) and request.httprequest.path.startswith("/web/dataset/call_button")

    @api.model
    def _action_open(self, records, method, messages):
        wizard = self.create(
            {"message": "\n\n".join(messages), "res_model": records._name, "res_ids": records.ids, "method": method}
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Confirm perceptions"),
            "res_model": self._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_confirm(self):
        self.ensure_one()
        records = self.env[self.res_model].browse(self.res_ids)
        return getattr(records.with_context(l10n_ar_perceptions_confirmed=True), self.method)()
