from odoo import fields, models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_ar_partner_vat = fields.Char(related='partner_id.l10n_ar_vat', string='CUIT del destinatario')

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
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
            for vals in res:
                vals.update({
                    'date_maturity': date_maturity,
                })
        return res

    @api.depends('payment_method_code', 'l10n_latam_check_id', 'check_number')
    def _compute_payment_method_description(self):
        check_payments = self.filtered(
            lambda x: x.payment_method_code in ['check_printing', 'new_third_party_checks', 'out_third_party_checks', 'in_third_party_checks'])
        for rec in check_payments:
            if rec.l10n_latam_check_id:
                checks_desc = rec.l10n_latam_check_id.check_number
            else:
                checks_desc = rec.check_number or ''
            name = "%s: %s" % (rec.payment_method_line_id.display_name, checks_desc)
            rec.payment_method_description = name
        return super(AccountPayment, (self - check_payments))._compute_payment_method_description()

    @api.onchange('l10n_latam_check_number')
    def _inverse_l10n_latam_check_number(self):
        """ Cuando se crea un payment group y no se guarda y luego se crean líneas de pago en dicho payment group de cheques de terceros indicando el número de cheque y posteriormente se guarda el payment group necesitamos que no se borre el banco que se indica en cada una de las líneas de pago. """
        for rec in self:
            rec.check_number = '%08d' % int(rec.l10n_latam_check_number) if rec.l10n_latam_check_number and rec.journal_id.company_id.country_id.code == "AR" and rec.l10n_latam_check_number.isdecimal() else rec.l10n_latam_check_number

    def _compute_l10n_latam_check_bank_id(self):
        """ Cuando se crea un payment group y no se guarda y luego se crean líneas de pago en dicho payment group de cheques de terceros indicando el banco correspondiente del cheque y posteriormente se guarda el payment group necesitamos que no se borre el banco que se indica en cada una de las líneas de pago. """
        new_third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
        for rec in new_third_party_checks:
            rec.l10n_latam_check_bank_id = rec.partner_id.bank_ids[:1].bank_id or rec.l10n_latam_check_bank_id
        (self - new_third_party_checks).l10n_latam_check_bank_id = False
