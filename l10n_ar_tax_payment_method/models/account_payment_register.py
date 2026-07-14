##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.depends("payment_method_line_id.l10n_ar_apply_withholding")
    def _compute_fiscal_position_id(self):
        super()._compute_fiscal_position_id()
        self._l10n_ar_clear_fiscal_position_if_disabled()

    def _l10n_ar_clear_fiscal_position_if_disabled(self):
        # La restricción del medio de pago prevalece en cada recálculo (también en modo manual):
        # si el método no aplica retenciones, se fuerza la posición fiscal a vacío. Filtramos primero
        # y solo escribimos si hay algo que limpiar, para no recursar cuando esto corre dentro de write().
        to_clear = self.filtered(
            lambda rec: rec.payment_method_line_id
            and not rec.payment_method_line_id.l10n_ar_apply_withholding
            and rec.l10n_ar_fiscal_position_id
        )
        if to_clear:
            to_clear.l10n_ar_fiscal_position_id = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._l10n_ar_clear_fiscal_position_if_disabled()
        return records

    def write(self, vals):
        # Un valor explícito a l10n_ar_fiscal_position_id no dispara el compute; lo forzamos en write
        # para que el preview de retenciones del wizard respete el flag del medio de pago.
        res = super().write(vals)
        if "l10n_ar_fiscal_position_id" in vals:
            self._l10n_ar_clear_fiscal_position_if_disabled()
        return res
