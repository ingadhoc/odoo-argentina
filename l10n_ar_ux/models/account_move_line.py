from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('currency_id', 'amount_currency')
    def _onchange_currency(self):
        """This method is a copy of the original one in account module, here we use the same logic if l10n_ar_currency_rate y setted"""
        force_currency_rate_lines = self.filtered(lambda x: x.move_id.l10n_ar_currency_rate)
        for line in force_currency_rate_lines:
            company = line.move_id.company_id
            if line.move_id.is_invoice(include_receipts=True):
                line.with_context(force_rate=line.move_id.l10n_ar_currency_rate)._onchange_price_subtotal()
            elif not line.move_id.reversed_entry_id:
                balance = line.currency_id.with_context(force_rate=line.move_id.l10n_ar_currency_rate)._convert(line.amount_currency, company.currency_id, company, line.move_id.date or fields.Date.context_today(line))
                line.debit = balance if balance > 0.0 else 0.0
                line.credit = -balance if balance < 0.0 else 0.0

        super(AccountMoveLine, self - force_currency_rate_lines)._onchange_currency()
