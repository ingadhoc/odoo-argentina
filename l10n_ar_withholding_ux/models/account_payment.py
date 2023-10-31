from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):

    _inherit = 'account.payment'


    l10n_ar_withholding_line_ids = fields.One2many(
        'l10n_ar.payment.withholding', 'payment_id', string='Withholdings',
        compute = '_compute_l10n_ar_withholding_line_ids', readonly=False, store = True
    )
    l10n_ar_amount_total = fields.Monetary('Amount Total', compute='_compute_l10n_ar_amount_total', readonly=True,  help="Total amount after withholdings")

    def _get_withholding_move_line_default_values(self):
        return {
            'currency_id': self.currency_id.id,
        }

    @api.depends('l10n_ar_withholding_line_ids.amount', 'amount', 'state')
    def _compute_l10n_ar_amount_total(self):
        for rec in self:
            rec.l10n_ar_amount_total = rec.amount + sum(rec.l10n_ar_withholding_line_ids.mapped('amount'))

    @api.depends('state', 'move_id')
    def _compute_l10n_ar_withholding_line_ids(self):
        for rec in self:
            l10n_ar_withholding_line_ids = [Command.clear()]
            for line in rec.move_id.line_ids.filtered(lambda x: x.tax_line_id):
                base = sum(rec.line_ids.filtered(lambda x: line.tax_line_id.id in x.tax_ids.ids).mapped('balance'))
                l10n_ar_withholding_line_ids += [Command.create({'name': line.name, 'tax_id': line.tax_line_id.id, 'base_amount': abs(base), 'amount': abs(line.balance)})]
            rec.l10n_ar_withholding_line_ids = l10n_ar_withholding_line_ids

    def _prepare_witholding_write_off_vals(self):

        self.ensure_one()
        write_off_line_vals = []
        #conversion_rate = self._get_conversion_rate()
        conversion_rate = 1
        sign = 1
        if self.partner_type == 'supplier':
            sign = -1
        for line in self.l10n_ar_withholding_line_ids:
            if not line.name:
                if line.tax_id.l10n_ar_withholding_sequence_id:
                    line.name = line.tax_id.l10n_ar_withholding_sequence_id.next_by_id()
                else:
                    raise UserError(_('Please enter withholding number for tax %s') % line.tax_id.name)
            dummy, account_id, tax_repartition_line_id = line._tax_compute_all_helper()
            balance = self.company_currency_id.round(line.amount * conversion_rate)
            write_off_line_vals.append({
                    **self._get_withholding_move_line_default_values(),
                    'name': line.name,
                    'account_id': account_id,
                    'amount_currency': sign * line.amount,
                    'balance': sign * balance,
                    'tax_base_amount': sign * line.base_amount,
                    'tax_repartition_line_id': tax_repartition_line_id,
            })

        for base_amount in list(set(self.l10n_ar_withholding_line_ids.mapped('base_amount'))):
            withholding_lines = self.l10n_ar_withholding_line_ids.filtered(lambda x: x.base_amount == base_amount)
            nice_base_label = ','.join(withholding_lines.mapped('name'))
            account_id = self.company_id.l10n_ar_tax_base_account_id.id
            base_amount = sign * base_amount
            cc_base_amount = self.company_currency_id.round(base_amount * conversion_rate)
            write_off_line_vals.append({
                **self._get_withholding_move_line_default_values(),
                'name': _('Base Ret: ') + nice_base_label,
                'tax_ids': [Command.set(withholding_lines.mapped('tax_id').ids)],
                'account_id': account_id,
                'balance': cc_base_amount,
                'amount_currency': base_amount,
            })
            write_off_line_vals.append({
                **self._get_withholding_move_line_default_values(),  # Counterpart 0 operation
                'name': _('Base Ret Cont: ') + nice_base_label,
                'account_id': account_id,
                'balance': -cc_base_amount,
                'amount_currency': -base_amount,
            })

        return write_off_line_vals

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ('l10n_ar_withholding_line_ids',)


    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res =  super()._prepare_move_line_default_vals(write_off_line_vals)
        res += self._prepare_witholding_write_off_vals()
        wth_amount = sum(self.l10n_ar_withholding_line_ids.mapped('amount'))
        #TODO: EVALUAR
        # si cambio el valor de la cuenta de liquides quitando las retenciones el campo amount representa el monto que cancelo de la deuda
        # si cambio la cuenta de contraparte (agregando retenciones) el campo amount representa el monto neto que abono al partner
        # Ambos caminos funcionan pero no se cual es mejor a nivel usabilidad. depende como realizemos el calculo autoatico de la ret
        #liquidity_accounts = [x.id for x in self._get_valid_liquidity_accounts() if x]
        valid_account_types = self._get_valid_payment_account_types()


        for line in res:
            account_id = self.env['account.account'].browse(line['account_id'])
            #if line['account_id'] in liquidity_accounts:
            if account_id.account_type in valid_account_types:
                if line['credit']:
                    line['credit'] += wth_amount
                    line['amount_currency'] -= wth_amount
                elif line['debit']:
                    line['debit'] += wth_amount
                    line['amount_currency'] += wth_amount
        return res

    def _get_conversion_rate(self):
        self.ensure_one()
        if self.currency_id != self.source_currency_id:
            return self.env['res.currency']._get_conversion_rate(
                self.currency_id,
                self.source_currency_id,
                self.company_id,
                self.payment_date,
            )
        return 1.0

class l10nArPaymentRegisterWithholding(models.TransientModel):
    _name = 'l10n_ar.payment.withholding'
    _description = 'Payment withholding lines'


    payment_id = fields.Many2one('account.payment', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='payment_id.company_id')
    currency_id = fields.Many2one(related='payment_id.currency_id')
    name = fields.Char(string='Number')
    tax_id = fields.Many2one('account.tax', check_company=True, required=True)
    withholding_sequence_id = fields.Many2one(related='tax_id.l10n_ar_withholding_sequence_id')
    # base_amount = fields.Monetary(compute='_compute_base_amount', store=True, readonly=False,
    #                               required=True)
    base_amount = fields.Monetary(required=True)
    amount = fields.Monetary(required=True, compute='_compute_amount', store=True, readonly=False)

    # def _compute_base_amount(self):


    def _tax_compute_all_helper(self):
        self.ensure_one()
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100
        taxes_res = self.tax_id.compute_all(
            self.base_amount,
            currency=self.payment_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        tax_amount = taxes_res['taxes'][0]['amount']
        tax_account_id = taxes_res['taxes'][0]['account_id']
        tax_repartition_line_id = taxes_res['taxes'][0]['tax_repartition_line_id']
        return tax_amount, tax_account_id, tax_repartition_line_id

    @api.depends('tax_id', 'base_amount')
    def _compute_amount(self):
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount, dummy, dummy = line._tax_compute_all_helper()
