from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from ast import literal_eval
from odoo.tools.safe_eval import safe_eval
from dateutil.relativedelta import relativedelta
import datetime


class AccountTax(models.Model):
    _inherit = "account.tax"

    withholding_non_taxable_amount = fields.Float(
        'Non-taxable Amount',
        digits='Account',
        help="Amount to be substracted before applying alicuot"
    )
    withholding_non_taxable_minimum = fields.Float(
        'Non-taxable Minimum',
        digits='Account',
        help="Amounts lower than this wont't have any withholding"
    )
    withholding_amount_type = fields.Selection([
        ('untaxed_amount', 'Untaxed Amount'),
        ('total_amount', 'Total Amount'),
        # ('percentage_of_total', 'Percentage Of Total'),
        # neto gravado + no gravado / neto gravado / importe total
        # importe de iva?
    ],
        'Base Amount',
        help='Base amount used to get withholding amount',
    )
    # base_amount_percentage = fields.Float(
    #     'Percentage',
    #     help="Enter % ratio between 0-1.",
    #     default=1,
    # )
    withholding_user_error_message = fields.Char(
    )
    withholding_user_error_domain = fields.Char(
        default="[]",
        help='Write a domain over account voucher module'
    )
    withholding_advances = fields.Boolean(
        'Advances are Withholdable?',
        default=True,
    )
    withholding_accumulated_payments = fields.Selection([
        ('month', 'Month'),
        ('year', 'Year'),
    ],
        string='Accumulated Payments',
        help='If none is selected, then payments are not accumulated',
    )
    # TODO implement
    # allow_modification = fields.Boolean(
    #     )
    withholding_type = fields.Selection([
        ('none', 'None'),
        # ('percentage', 'Percentage'),
        ('based_on_rule', 'Based On Rule'),
        # ('fixed', 'Fixed Amount'),
        ('code', 'Python Code'),
        # ('balance', 'Balance')
    ],
        'Type',
        required=True,
        default='none',
        help="The computation method for the tax amount."
    )
    withholding_python_compute = fields.Text(
        'Python Code (withholdings)',
        default='''
# withholdable_base_amount
# payment: account.payment.group object
# partner: res.partner object (commercial partner of payment group)
# withholding_tax: account.tax.withholding object

result = withholdable_base_amount * 0.10
        ''',
    )
    withholding_rule_ids = fields.One2many(
        'account.tax.withholding.rule',
        'tax_withholding_id',
        'Rules',
    )
    # amount = fields.Float(
    #     'Amount',
    #     # digits='Account',
    #     help="For taxes of type percentage, enter % ratio between 0-1."
    #     )

    @api.constrains(
        'withholding_non_taxable_amount',
        'withholding_non_taxable_minimum')
    def check_withholding_non_taxable_amounts(self):
        for rec in self:
            if (
                    rec.withholding_non_taxable_amount >
                    rec.withholding_non_taxable_minimum):
                raise ValidationError(_(
                    'Non-taxable Amount can not be greater than Non-taxable '
                    'Minimum'))

    def _get_rule(self, voucher):
        self.ensure_one()
        # do not return rule if other type
        if self.withholding_type != 'based_on_rule':
            return False
        for rule in self.withholding_rule_ids:
            try:
                domain = literal_eval(rule.domain)
            except Exception as e:
                raise ValidationError(_(
                    'Could not eval rule domain "%s".\n'
                    'This is what we get:\n%s' % (rule.domain, e)))
            domain.append(('id', '=', voucher.id))
            applies = voucher.search(domain)
            if applies:
                return rule
        return False

    def create_payment_withholdings(self, payment_group):
        for tax in self.filtered(lambda x: x.withholding_type != 'none'):
            payment_withholding = self.env[
                'account.payment'].search([
                    ('payment_group_id', '=', payment_group.id),
                    ('tax_withholding_id', '=', tax.id),
                    ('automatic', '=', True),
                ], limit=1)
            if (
                    tax.withholding_user_error_message and
                    tax.withholding_user_error_domain):
                try:
                    domain = literal_eval(tax.withholding_user_error_domain)
                except Exception as e:
                    raise ValidationError(_(
                        'Could not eval rule domain "%s".\n'
                        'This is what we get:\n%s' % (
                            tax.withholding_user_error_domain, e)))
                domain.append(('id', '=', payment_group.id))
                if payment_group.search(domain):
                    raise ValidationError(tax.withholding_user_error_message)
            vals = tax.get_withholding_vals(payment_group)

            # we set computed_withholding_amount, hacemos round porque
            # si no puede pasarse un valor con mas decimales del que se ve
            # y terminar dando error en el asiento por debitos y creditos no
            # son iguales, algo parecido hace odoo en el compute_all de taxes
            currency = payment_group.currency_id
            period_withholding_amount = currency.round(vals.get(
                'period_withholding_amount', 0.0))
            previous_withholding_amount = currency.round(vals.get(
                'previous_withholding_amount'))
            # withholding can not be negative
            computed_withholding_amount = max(0, (
                period_withholding_amount - previous_withholding_amount))

            if not computed_withholding_amount:
                # if on refresh no more withholding, we delete if it exists
                if payment_withholding:
                    payment_withholding.unlink()
                continue

            # we copy withholdable_base_amount on base_amount
            # al final vimos con varios clientes que este monto base
            # debe ser la base imponible de lo que se está pagando en este
            # voucher
            vals['withholding_base_amount'] = vals.get(
                'withholdable_advanced_amount') + vals.get(
                'withholdable_invoiced_amount')
            vals['amount'] = computed_withholding_amount
            vals['computed_withholding_amount'] = computed_withholding_amount

            # por ahora no imprimimos el comment, podemos ver de llevarlo a
            # otro campo si es de utilidad
            vals.pop('comment')
            if payment_withholding:
                payment_withholding.write(vals)
            else:
                # TODO implementar devoluciones de retenciones
                payment_method = self.env.ref(
                    'account_withholding.'
                    'account_payment_method_out_withholding')
                journal = self.env['account.journal'].search([
                    ('company_id', '=', tax.company_id.id),
                    ('outbound_payment_method_line_ids.payment_method_id', '=', payment_method.id),
                    ('type', 'in', ['cash', 'bank']),
                ], limit=1)
                if not journal:
                    raise UserError(_(
                        'No journal for withholdings found on company %s') % (
                        tax.company_id.name))

                method = journal._get_available_payment_method_lines('outbound').filtered(
                    lambda x: x.code == 'withholding')

                vals['journal_id'] = journal.id
                vals['payment_method_line_id'] = method.id
                vals['payment_type'] = 'outbound'
                vals['partner_type'] = payment_group.partner_type
                vals['partner_id'] = payment_group.partner_id.id
                payment_withholding = payment_withholding.create(vals)
        return True

    def get_period_payments_domain(self, payment_group):
        """
        We make this here so it can be inherited by localizations
        """
        to_date = fields.Date.from_string(
            payment_group.payment_date) or datetime.date.today()
        if self.withholding_accumulated_payments == 'month':
            from_relative_delta = relativedelta(day=1)
        elif self.withholding_accumulated_payments == 'year':
            from_relative_delta = relativedelta(day=1, month=1)
        from_date = to_date + from_relative_delta

        previous_payment_groups_domain = [
            ('partner_id.commercial_partner_id', '=', payment_group.commercial_partner_id.id),
            ('payment_date', '<=', to_date),
            ('payment_date', '>=', from_date),
            ('state', 'not in', ['draft', 'cancel', 'confirmed']),
            ('id', '!=', payment_group.id),
            ('company_id', '=', payment_group.company_id.id),
        ]
        # for compatibility with public_budget we check state not in and not
        # state in posted. Just in case someone implements payments cancelled
        # on posted payment group, we remove the cancel payments (not the
        # draft ones as they are also considered by public_budget)
        previous_payments_domain = [
            ('partner_id.commercial_partner_id', '=', payment_group.commercial_partner_id.id),
            ('date', '<=', to_date),
            ('date', '>=', from_date),
            ('payment_group_id.state', 'not in',
                ['draft', 'cancel', 'confirmed']),
            ('state', '!=', 'cancel'),
            ('tax_withholding_id', '=', self.id),
            ('payment_group_id.id', '!=', payment_group.id),
        ]
        return (previous_payment_groups_domain, previous_payments_domain)

    def get_withholding_vals(
            self, payment_group, force_withholding_amount_type=None):
        """
        If you wan to inherit and implement your own type, the most important
        value tu return are period_withholding_amount and
        previous_withholding_amount, with thos values the withholding amount
        will be calculated.
        """
        self.ensure_one()
        withholding_amount_type = force_withholding_amount_type or \
            self.withholding_amount_type
        withholdable_advanced_amount, withholdable_invoiced_amount = \
            payment_group._get_withholdable_amounts(
                withholding_amount_type, self.withholding_advances)

        accumulated_amount = previous_withholding_amount = 0.0

        if self.withholding_accumulated_payments:
            previos_payment_groups_domain, previos_payments_domain = (
                self.get_period_payments_domain(payment_group))
            same_period_payments = self.env['account.payment.group'].search(
                previos_payment_groups_domain)

            for same_period_payment_group in same_period_payments:
                same_period_amounts = \
                    same_period_payment_group._get_withholdable_amounts(
                        withholding_amount_type, self.withholding_advances)
                accumulated_amount += \
                    same_period_amounts[0] + same_period_amounts[1]
            previous_withholding_amount = sum(
                self.env['account.payment'].search(
                    previos_payments_domain).mapped('amount'))

        total_amount = (
            accumulated_amount +
            withholdable_advanced_amount +
            withholdable_invoiced_amount)
        withholding_non_taxable_minimum = self.withholding_non_taxable_minimum
        withholding_non_taxable_amount = self.withholding_non_taxable_amount
        withholdable_base_amount = (
            (total_amount > withholding_non_taxable_minimum) and
            (total_amount - withholding_non_taxable_amount) or 0.0)

        comment = False
        if self.withholding_type == 'code':
            localdict = {
                'withholdable_base_amount': withholdable_base_amount,
                'payment': payment_group,
                'partner': payment_group.commercial_partner_id,
                'withholding_tax': self,
            }
            safe_eval(
                self.withholding_python_compute, localdict,
                mode="exec", nocopy=True)
            period_withholding_amount = localdict['result']
        else:
            rule = self._get_rule(payment_group)
            percentage = 0.0
            fix_amount = 0.0
            if rule:
                percentage = rule.percentage
                fix_amount = rule.fix_amount
                comment = '%s x %s + %s' % (
                    withholdable_base_amount,
                    percentage,
                    fix_amount)

            period_withholding_amount = (
                (total_amount > withholding_non_taxable_minimum) and (
                    withholdable_base_amount * percentage + fix_amount) or 0.0)

        return {
            'withholdable_invoiced_amount': withholdable_invoiced_amount,
            'withholdable_advanced_amount': withholdable_advanced_amount,
            'accumulated_amount': accumulated_amount,
            'total_amount': total_amount,
            'withholding_non_taxable_minimum': withholding_non_taxable_minimum,
            'withholding_non_taxable_amount': withholding_non_taxable_amount,
            'withholdable_base_amount': withholdable_base_amount,
            'period_withholding_amount': period_withholding_amount,
            'previous_withholding_amount': previous_withholding_amount,
            'payment_group_id': payment_group.id,
            'currency_id': payment_group.currency_id.id,
            'tax_withholding_id': self.id,
            'automatic': True,
            'comment': comment,
        }
