##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.tools import float_round


class AccountMoveChangeRate(models.TransientModel):
    _name = 'account.move.change.rate'
    _description = 'account.move.change.rate'

    @api.model
    def get_move(self):
        move = self.env['account.move'].browse(
            self._context.get('active_id', False))
        return move

    currency_rate = fields.Float(
        'Currency Rate',
        required=True,
        digits=(16, 6),
        help="Select a rate to apply on the invoice"
    )
    move_id = fields.Many2one(
        'account.move',
        default=get_move
    )

    day_rate = fields.Boolean(
        string="Use currency rate of the day", help="The currency rate on the invoice date will be used. If the invoice does not have a date, the currency rate will be used at the time of validation.")

    @api.onchange('move_id')
    def _onchange_move(self):
        self.currency_rate = self.move_id.l10n_ar_currency_rate or self.move_id.computed_currency_rate

    def confirm(self):
        if self.day_rate:
            message = _("The forced rate '%s' was removed, date rate will be use") % (self.move_id.l10n_ar_currency_rate)
            rate = 0.0
        else:
            message = _("Currency rate changed from '%s' to '%s' . Currency rate forced") % (float_round(self.move_id.l10n_ar_currency_rate or self.move_id.computed_currency_rate, 2), float_round(self.currency_rate, 2))
            rate = self.currency_rate
        # pasamos el tax_totals porque es lo que termina usando  account_invoice_tax para poder mantener impuestos forzados
        # lo podemos hacer aca de anera segura porque sabemos que solo cambia rate y no cambia ningun importe
        self.move_id.write({'l10n_ar_currency_rate': rate, 'tax_totals': self.move_id.tax_totals})
        self.move_id.message_post(body=message)
        return {'type': 'ir.actions.act_window_close'}
