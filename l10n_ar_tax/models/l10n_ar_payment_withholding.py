from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime


class l10nArPaymentRegisterWithholding(models.Model):
    _name = 'l10n_ar.payment.withholding'
    _description = 'Payment withholding lines'

    payment_id = fields.Many2one('account.payment', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='payment_id.company_id')
    currency_id = fields.Many2one(related='payment_id.company_currency_id')
    l10n_ar_tax_type = fields.Selection(related='tax_id.l10n_ar_tax_type')
    name = fields.Char(string='Number')
    ref = fields.Text(compute='_compute_amount', store=True, readonly=False)
    tax_id = fields.Many2one('account.tax', check_company=True, required=True)
    withholding_sequence_id = fields.Many2one(related='tax_id.l10n_ar_withholding_sequence_id')
    base_amount = fields.Monetary(compute='_compute_base_amount', store=True, readonly=False)
    # por ahora dejamos amount a mano como era antes y que solo se compute con el compute withholdings desde arriba
    # luego vemos de hacer que toda la logica este acá
    amount = fields.Monetary(compute='_compute_amount', store=True, readonly=False)

    _sql_constraints = [('uniq_line', 'unique(tax_id, payment_id)', "El impuesto de retención debe ser único por pago")]

    @api.depends(
        'tax_id',
        'payment_id.selected_debt',
        'payment_id.selected_debt_untaxed',
        'payment_id.unreconciled_amount',
    )
    def _compute_base_amount(self):
        """ practicamente mismo codigo que en l10n_ar.payment.register.withholding pero usamos campos "selected_debt_"""
        for wth in self:
            # calculamos advance_amount
            # si el adelanto es negativo estamos pagando parcialmente una
            # factura y ocultamos el campo sin impuesto y el metodo _get_withholdable_advanced_amount nos devuelve
            # el proporcional descontando de el iva a lo que se esta pagando
            advance_amount = wth.payment_id.withholdable_advanced_amount
            if advance_amount < 0.0:
                sorted_to_pay_lines = sorted(wth.payment_id.to_pay_move_line_ids, key=lambda a: a.date_maturity or a.date)
                # last line to be reconciled
                partial_line = sorted_to_pay_lines[-1]
                if -partial_line.amount_residual < -wth.payment_id.withholdable_advanced_amount:
                    raise UserError(_(
                        'Seleccionó deuda por %s pero aparentente desea pagar '
                        '%s. En la deuda seleccionada hay algunos comprobantes de '
                        'mas que no van a poder ser pagados (%s). Deberá quitar '
                        'dichos comprobantes de la deuda seleccionada para poder '
                        'hacer el correcto cálculo de las retenciones.' % (
                            wth.payment_id.selected_debt,
                            wth.payment_id.to_pay_amount,
                            partial_line.move_id.display_name,
                    )))
                advance_amount = wth.payment_id.unreconciled_amount
                if wth.tax_id.l10n_ar_tax_type != 'iibb_total':
                    advance_amount = advance_amount * (wth.payment_id.selected_debt_untaxed / wth.payment_id.selected_debt)

            if wth.tax_id.l10n_ar_tax_type == 'iibb_total':
                wth.base_amount = wth.payment_id.selected_debt + advance_amount
            else:
                wth.base_amount = wth.payment_id.selected_debt_untaxed + advance_amount

    def _tax_compute_all_helper(self):
        """ practicamente mismo codigo que en l10n_ar.payment.register.withholding """
        self.ensure_one()
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100

        # if it is earnings withholding, then we accumulate the tax base for the period
        if self.tax_id.l10n_ar_tax_type in ['earnings', 'earnings_scale']:
            to_date = self.payment_id.date or datetime.date.today()
            from_date = to_date + relativedelta(day=1)
            # We search for the payments in the same month of the same regimen and the same code.
            domain_same_period_withholdings = [
                *self.env['account.move.line']._check_company_domain(self.tax_id.company_id),
                ('parent_state', '=', 'posted'),
                ('tax_line_id.l10n_ar_code', '=', self.tax_id.l10n_ar_code),
                ('tax_line_id.l10n_ar_tax_type', 'in', ['earnings', 'earnings_scale']),
                ('partner_id', '=', self.payment_id.partner_id.commercial_partner_id.id),
                ('date', '<=', to_date), ('date', '>=', from_date)]
            if same_period_partner_withholdings := self.env['account.move.line']._read_group(domain_same_period_withholdings, ['partner_id'], ['balance:sum']):
                same_period_withholdings = abs(same_period_partner_withholdings[0][1])
            else:
                same_period_withholdings = 0.0
            domain_same_period_base = [
                *self.env['account.move.line']._check_company_domain(self.tax_id.company_id),
                ('parent_state', '=', 'posted'),
                ('tax_ids.l10n_ar_code', '=', self.tax_id.l10n_ar_code),
                ('tax_ids.l10n_ar_tax_type', 'in', ['earnings', 'earnings_scale']),
                ('partner_id', '=', self.payment_id.partner_id.commercial_partner_id.id),
                ('date', '<=', to_date), ('date', '>=', from_date)]
            if same_period_partner_base := self.env['account.move.line']._read_group(domain_same_period_base, ['partner_id'], ['balance:sum']):
                same_period_base = abs(same_period_partner_base[0][1])
            else:
                same_period_base = 0.0
            net_amount = self.base_amount + same_period_base
        else:
            net_amount = self.base_amount
        net_amount = max(0, net_amount - self.tax_id.l10n_ar_non_taxable_amount)
        taxes_res = self.tax_id.compute_all(
            net_amount,
            currency=self.payment_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        tax_amount = taxes_res['taxes'][0]['amount']
        tax_account_id = taxes_res['taxes'][0]['account_id']
        tax_repartition_line_id = taxes_res['taxes'][0]['tax_repartition_line_id']

        ref = False
        if self.tax_id.l10n_ar_tax_type in ['earnings', 'earnings_scale']:
            f = self.currency_id.format
            if net_amount <= 0:
                ref = "{base_amount} + {same_period_base} - {non_taxable_amount} = {net_amount} (no corresponde aplicar)".format(
                    base_amount=f(self.base_amount),
                    same_period_base=f(same_period_base),
                    non_taxable_amount=f(self.tax_id.l10n_ar_non_taxable_amount),
                    net_amount=f(self.base_amount + same_period_base - self.tax_id.l10n_ar_non_taxable_amount),
                )
            # if it is earnings scale we calculate according to the scale.
            if self.tax_id.l10n_ar_tax_type == 'earnings_scale':
                escala = self.env['l10n_ar.earnings.scale.line'].search([
                    ('scale_id', '=', self.tax_id.l10n_ar_scale_id.id),
                    ('excess_amount', '<=', net_amount),
                    ('to_amount', '>', net_amount),
                ], limit=1)
                tax_amount = ((net_amount - escala.excess_amount) * escala.percentage / 100) + escala.fixed_amount
                # for eg. (1000000.0 + 0.0 - 7870.0 - 1231231) * 7.0 % + 1231231 - 0.0
                ref = ref or "({base_amount} + {same_period_base} - {non_taxable_amount} - {excess_amount}) * {aliquot}% + {fixed_amount} - {same_period_withholdings}".format(
                    base_amount=f(self.base_amount),
                    same_period_base=f(same_period_base),
                    non_taxable_amount=f(self.tax_id.l10n_ar_non_taxable_amount),
                    excess_amount = f(escala.excess_amount),
                    aliquot=escala.percentage,
                    fixed_amount=f(escala.fixed_amount),
                    same_period_withholdings=f(same_period_withholdings),
                )
            else:
                # for eg. (1000000.0 + 0.0 - 7870.0) * 7.0% - 0.0
                ref = "({base_amount} + {same_period_base} - {non_taxable_amount}) * {aliquot}% - {same_period_withholdings}".format(
                    base_amount=f(self.base_amount),
                    same_period_base=f(same_period_base),
                    non_taxable_amount=f(self.tax_id.l10n_ar_non_taxable_amount),
                    aliquot=self.tax_id.amount,
                    same_period_withholdings=f(same_period_withholdings),
                )
            # deduct withholdings from the same period
            tax_amount -= same_period_withholdings

        l10n_ar_minimum_threshold = self.tax_id.l10n_ar_minimum_threshold
        if l10n_ar_minimum_threshold > tax_amount:
            tax_amount = 0.0
        return tax_amount, tax_account_id, tax_repartition_line_id, ref

    @api.depends('base_amount', 'tax_id')
    def _compute_amount(self):
        import pdb; pdb.set_trace()
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
                line.ref = False
            else:
                tax_amount, __, __, ref = line._tax_compute_all_helper()
                line.amount = tax_amount
                line.ref = ref
