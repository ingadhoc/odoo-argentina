from odoo import fields, models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_ar_partner_vat = fields.Char(related='partner_id.l10n_ar_vat', string='CUIT del destinatario')
    l10n_latam_check_printing_type = fields.Selection(related='l10n_latam_checkbook_id.check_printing_type')

    @api.model
    def _get_trigger_fields_to_sincronize(self):
        res = super()._get_trigger_fields_to_sincronize()
        return res + ('l10n_latam_check_payment_date',)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ Add check name and operation on liquidity line """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        date_maturity = False
        check = self if self.payment_method_line_id.code == 'new_third_party_checks' else self.l10n_latam_check_id
        if check:
            date_maturity = check.l10n_latam_check_payment_date
        elif self.payment_method_line_id.code == 'check_printing' and self.l10n_latam_check_payment_date:
            date_maturity = self.l10n_latam_check_payment_date
        if date_maturity:
            res[0].update({
                'date_maturity': date_maturity,
            })
        return res

    @api.depends('journal_id', 'payment_method_code', 'l10n_latam_checkbook_id')
    def _compute_check_number(self):
        print_checkbooks = self.filtered(lambda x: x.l10n_latam_checkbook_id.check_printing_type != 'no_print')
        print_checkbooks.check_number = False
        return super(AccountPayment, self - print_checkbooks)._compute_check_number()

    def action_mark_sent(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        self.write({'is_move_sent': True})

    def action_unmark_sent(self):
        # restore action_unmark_sent functionality (it was cancelled l10n_latam_check)
        if self.filtered('l10n_latam_checkbook_id'):
            self.write({'is_move_sent': False})
        else:
            return super().action_unmark_sent()
