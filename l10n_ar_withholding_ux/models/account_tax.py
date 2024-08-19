from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
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

    def get_period_payments_domain(self, payment):
        """
        We make this here so it can be inherited by localizations
        Para un determinado pago (para saber fecha, impuesto y demas) obtenemos dos dominios:
        * previous_payments_domain: dominio para hacer search de payments que nos devuelva los pagos del mismo mes
        que son base de este impuesto (por ej. en ganancias de mismo regimen y que aplica impuesto)
        * previous_withholdings_domain: dominio para hacer search del impuesto aplicado en el mes
        """
        to_date = fields.Date.from_string(payment.date) or datetime.date.today()
        if self.withholding_accumulated_payments == 'month':
            from_relative_delta = relativedelta(day=1)
        elif self.withholding_accumulated_payments == 'year':
            from_relative_delta = relativedelta(day=1, month=1)
        from_date = to_date + from_relative_delta

        previous_payments_domain = [
            ('partner_id.commercial_partner_id', '=', payment.partner_id.commercial_partner_id.id),
            ('date', '<=', to_date),
            ('date', '>=', from_date),
            ('state', 'not in', ['draft', 'cancel', 'confirmed']),
            ('company_id', '=', payment.company_id.id),
        ]

        # for compatibility with public_budget we check state not in and not
        # state in posted. Just in case someone implements payments cancelled
        # on posted payment group, we remove the cancel payments (not the
        # draft ones as they are also considered by public_budget)
        previous_withholdings_domain = [
            ('payment_id.partner_id.commercial_partner_id', '=', payment.partner_id.commercial_partner_id.id),
            ('payment_id.date', '<=', to_date),
            ('payment_id.date', '>=', from_date),
            ('payment_id.state', '=', 'posted'),
            ('tax_id', '=', self.id),
        ]

        if not isinstance(payment.id, models.NewId):
            previous_payments_domain.append(('id', '!=', payment.id))
            previous_withholdings_domain.append(('payment_id.id', '!=', payment.id))

        return (previous_payments_domain, previous_withholdings_domain)

    def get_withholding_vals(self, payment, force_withholding_amount_type=None):
        """
        If you wan to inherit and implement your own type, the most important
        value tu return are period_withholding_amount and
        previous_withholding_amount, with thos values the withholding amount
        will be calculated.
        """
        self.ensure_one()
        withholding_amount_type = force_withholding_amount_type or self.withholding_amount_type
        withholdable_advanced_amount, withholdable_invoiced_amount = payment._get_withholdable_amounts(
            withholding_amount_type, self.withholding_advances)

        accumulated_amount = previous_withholding_amount = 0.0

        if self.withholding_accumulated_payments:
            previous_payments_domain, previous_withholdings_domain = (self.get_period_payments_domain(payment))
            same_period_payments = self.env['account.payment'].search(previous_payments_domain)

            for same_period_payment in same_period_payments:
                same_period_amounts = same_period_payment._get_withholdable_amounts(
                    withholding_amount_type, self.withholding_advances)
                accumulated_amount += same_period_amounts[0] + same_period_amounts[1]
            previous_withholding_amount = sum(
                self.env['l10n_ar.payment.withholding'].search(previous_withholdings_domain).mapped('amount'))

        total_amount = accumulated_amount + withholdable_advanced_amount + withholdable_invoiced_amount
        withholding_non_taxable_minimum = self.withholding_non_taxable_minimum
        withholding_non_taxable_amount = self.withholding_non_taxable_amount
        withholdable_base_amount = (
            (total_amount > withholding_non_taxable_minimum) and
            (total_amount - withholding_non_taxable_amount) or 0.0)

        comment = False
        if self.withholding_type == 'code':
            localdict = {
                'withholdable_base_amount': withholdable_base_amount,
                'payment': payment,
                'partner': payment.commercial_partner_id,
                'withholding_tax': self,
            }
            safe_eval(self.withholding_python_compute, localdict, mode="exec", nocopy=True)
            period_withholding_amount = localdict['result']
        else:
            rule = self._get_rule(payment)
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
            'tax_id': self.id,
            'automatic': True,
            'comment': comment,
        }
