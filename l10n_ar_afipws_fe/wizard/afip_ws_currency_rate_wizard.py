##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AfipWsCurrencyRateWizard(models.TransientModel):
    _name = 'afip.ws.currency_rate.wizard'
    _description = 'AFIP WS Currency Rate Wizard'

    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        required=True,
    )

    @api.multi
    def confirm(self):
        self.ensure_one()
        journal_id = self._context.get('active_id', False)
        if not journal_id:
            raise UserError(_(
                'No Journal Id as active_id on context'))
        journal = self.env[
            'account.journal'].browse(journal_id)
        return journal.get_pyafipws_currency_rate(self.currency_id)
