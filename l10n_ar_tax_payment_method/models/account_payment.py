##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("payment_method_line_id.l10n_ar_apply_withholding")
    def _compute_fiscal_position_id(self):
        # Odoo acumula los depends de todos los overrides del método en el MRO, así que este
        # decorador se suma a los del módulo base sin reemplazarlos.
        super()._compute_fiscal_position_id()
        self._l10n_ar_clear_fiscal_position_if_disabled()

    @api.depends("payment_method_line_id.l10n_ar_apply_withholding")
    def _compute_l10n_ar_allowed_fiscal_position_ids(self):
        super()._compute_l10n_ar_allowed_fiscal_position_ids()
        self.filtered(
            lambda rec: rec.payment_method_line_id and not rec.payment_method_line_id.l10n_ar_apply_withholding
        ).l10n_ar_allowed_fiscal_position_ids = False

    def _l10n_ar_clear_fiscal_position_if_disabled(self):
        # La restricción a nivel medio de pago prevalece: si el método no aplica retenciones,
        # forzamos la posición fiscal a vacío para que no se calculen. Filtramos primero y solo
        # escribimos si hay algo que limpiar: así, cuando esto corre dentro de write(), la re-entrada
        # encuentra el conjunto vacío y no hay recursión infinita.
        # Only drafts: a posted payment keeps the position its withholding lines were computed with.
        to_clear = self.filtered(
            lambda rec: rec.state == "draft"
            and rec.payment_method_line_id
            and not rec.payment_method_line_id.l10n_ar_apply_withholding
            and rec.l10n_ar_fiscal_position_id
        )
        if to_clear:
            to_clear.l10n_ar_fiscal_position_id = False

    @api.model_create_multi
    def create(self, vals_list):
        # El campo es compute store + readonly=False (editable). Un valor pasado directo en create
        # no dispara el compute, así que reforzamos la restricción del medio de pago acá también.
        records = super().create(vals_list)
        records._l10n_ar_clear_fiscal_position_if_disabled()
        return records

    def write(self, vals):
        # Un valor explícito a l10n_ar_fiscal_position_id no dispara el compute, así que lo forzamos
        # también en write para que no se pueda "saltear" el flag del medio de pago. Cambiar el método
        # de pago sí dispara el compute (depende de payment_method_line_id.l10n_ar_apply_withholding),
        # por eso ese caso no hace falta contemplarlo acá.
        withheld = {}
        # an explicit fiscal position comes with the amount the caller wants, so only a change of
        # method can leave a netted amount behind
        if "l10n_ar_fiscal_position_id" not in vals and {"payment_method_line_id", "journal_id"} & vals.keys():
            withheld = self._l10n_ar_get_withheld_amounts()
        res = super().write(vals)
        if "l10n_ar_fiscal_position_id" in vals:
            self._l10n_ar_clear_fiscal_position_if_disabled()
        self._l10n_ar_restore_withheld_amounts(withheld)
        return res

    def _l10n_ar_get_withheld_amounts(self):
        """Withholdings and amount of the saved drafts that have a fiscal position, by payment id.

        Taken before the position can be cleared: the onchange that nets the amount only runs in
        the form, so a draft that loses its withholdings on the server keeps the net amount.
        """
        return {
            rec.id: (rec.withholdings_amount, rec.amount)
            for rec in self
            if rec.id and rec.state == "draft" and rec.l10n_ar_fiscal_position_id and rec.withholdings_amount
        }

    def _l10n_ar_restore_withheld_amounts(self, withheld):
        """Add back to the amount the withholdings a draft lost with its fiscal position, unless
        something else already changed the amount (e.g. a change of journal resets it)."""
        for rec in self.filtered(
            lambda rec: rec.id in withheld
            and rec.state == "draft"
            and not rec.l10n_ar_fiscal_position_id
            and rec.currency_id.compare_amounts(rec.amount, withheld[rec.id][1]) == 0
        ):
            rec.amount += rec._l10n_ar_destination_to_amount_currency(withheld[rec.id][0])
