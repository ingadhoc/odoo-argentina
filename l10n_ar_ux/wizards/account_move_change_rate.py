##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


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

<<<<<<< HEAD
    day_rate = fields.Boolean(
        string="Use currency rate of the day", help="The currency rate on the invoice date will be used. If the invoice does not have a date, the currency rate will be used at the time of validation.")

||||||| parent of b2f2fc30... temp
=======
    @api.constrains('currency_rate')
    def _prevent_change_currency(self):
        """prevent currency change when the invoice is not draft
        """
        if self.move_id.state != 'draft':
            raise ValidationError(_('This invoice is not draft, reset it to draft to change currency rate'))

>>>>>>> b2f2fc30... temp
    @api.onchange('move_id')
    def _onchange_move(self):
        self.currency_rate = self.move_id.l10n_ar_currency_rate or self.move_id.computed_currency_rate

    def confirm(self):
        if self.day_rate:
            message = _("Currency rate changed from %s to %s") % (self.move_id.l10n_ar_currency_rate or self.move_id.computed_currency_rate, self.move_id.computed_currency_rate)
            self.move_id.l10n_ar_currency_rate = 0.0
        else:
            message = _("Currency rate changed from %s to %s . Currency rate forced") % (self.move_id.l10n_ar_currency_rate or self.move_id.computed_currency_rate, self.currency_rate)
            self.move_id.l10n_ar_currency_rate = self.currency_rate
        self.move_id.message_post(body=message)
        return {'type': 'ir.actions.act_window_close'}
