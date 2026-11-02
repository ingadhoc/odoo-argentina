from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.addons.l10n_ar_withholding.models.account_tax import EARNINGS_TAX_TYPES
from odoo.exceptions import RedirectWarning, UserError


class AccountPaymentWithholdingLine(models.Model):
    _inherit = "account.payment.withholding.line"

    l10n_ar_withholding_tax_type = fields.Selection(related="tax_id.l10n_ar_withholding_tax_type")
    ref = fields.Text(compute="_compute_amount", store=True, readonly=False)

    def _l10n_ar_get_computable_withholdings(self):
        """Lines whose base and amount we compute: supplier withholdings of a draft payment pro payment.

        The base comes from the current residual of the invoices, which keeps moving after posting, so a non draft
        payment keeps the stored values of its journal entry. ``payment_id.state`` is not in the depends on purpose:
        posting must not trigger a recompute. The rest of the lines keep the computation of Odoo.
        """
        return self.filtered(
            lambda x: x.payment_id.state == "draft"
            and x.payment_id.use_payment_pro
            and x.payment_id.partner_type == "supplier"
            and x.country_code == "AR"
            and x.tax_id.type_tax_use == "purchase"
        )

    def _l10n_ar_get_company_to_line_rate(self):
        """Rate to go from the company currency (C, where the AR rules apply) to the payment currency (A, the one of
        the line): the rate of the payment, the same one that values its journal entry."""
        self.ensure_one()
        pay = self.payment_id
        if pay.currency_id == pay.company_currency_id:
            return 1.0
        return pay.accounting_rate or 1.0

    @api.depends(
        "tax_id",
        "payment_id.selected_debt",
        "payment_id.selected_debt_untaxed",
        "payment_id.withholdable_advanced_amount",
        "payment_id.unreconciled_amount",
        "payment_id.counterpart_rate",
        "payment_id.accounting_rate",
    )
    def _compute_base_amount(self):
        computable = self._l10n_ar_get_computable_withholdings()
        super(AccountPaymentWithholdingLine, self - computable)._compute_base_amount()
        computable.payment_id._compute_to_pay_amount()
        for wth in computable:
            base_in_c = wth._l10n_ar_get_base_company_currency()
            wth.base_amount = wth.comodel_currency_id.round(base_in_c * wth._l10n_ar_get_company_to_line_rate())

    def _l10n_ar_get_base_company_currency(self):
        """Base over the selected debt (untaxed, or with taxes for 'iibb_total') plus the advance, in company
        currency, with the ratio of the tax applied."""
        self.ensure_one()
        pay = self.payment_id
        tax = self.tax_id
        # si el adelanto es negativo estamos pagando parcialmente una factura y
        # _get_withholdable_advanced_amount nos devuelve el proporcional descontando el iva de lo que se paga
        advance_amount = pay.withholdable_advanced_amount
        if advance_amount < 0.0 and pay.to_pay_move_line_ids:
            sorted_to_pay_lines = sorted(pay.to_pay_move_line_ids, key=lambda a: a.date_maturity or a.date)
            # last line to be reconciled
            partial_line = sorted_to_pay_lines[-1]
            # Comparar en moneda B (ambos lados)
            if pay.destination_currency_id and pay.destination_currency_id != pay.company_currency_id:
                line_residual = abs(partial_line.amount_residual_currency)
            else:
                line_residual = abs(partial_line.amount_residual)
            if line_residual < abs(pay.withholdable_advanced_amount):
                raise UserError(
                    _(
                        "You selected a debt of %s but apparently want to pay %s. The selected debt includes some documents that cannot be paid (%s). You must remove those documents from the selected debt to correctly calculate withholdings."
                    )
                    % (
                        pay.selected_debt,
                        pay.to_pay_amount,
                        partial_line.move_id.display_name,
                    )
                )
            advance_amount = pay.unreconciled_amount
            if tax.l10n_ar_withholding_tax_type != "iibb_total":
                advance_amount = advance_amount * (pay.selected_debt_untaxed / pay.selected_debt)

        if tax.l10n_ar_withholding_tax_type == "iibb_total":
            base_in_b = pay.selected_debt + advance_amount
        else:
            base_in_b = pay.selected_debt_untaxed + advance_amount
        base_in_c = pay.company_currency_id.round(base_in_b * pay._get_withholding_rate())
        if tax.amount_type == "percent" and tax.ratio != 100:
            base_in_c *= tax.ratio / 100
        return base_in_c

    @api.depends("base_amount", "tax_id")
    def _compute_amount(self):
        computable = self._l10n_ar_get_computable_withholdings()
        super(AccountPaymentWithholdingLine, self - computable)._compute_amount()
        for line in computable:
            if not line.tax_id:
                line.amount = 0.0
                line.ref = False
                continue
            amount_in_c, ref = line._l10n_ar_compute_withholding()
            line.amount = line.comodel_currency_id.round(amount_in_c * line._l10n_ar_get_company_to_line_rate())
            line.ref = ref

    def _l10n_ar_compute_withholding(self):
        """Withholding amount in company currency and the formula shown to the user, over the base of the line.

        Earnings: base plus what was paid to the partner this month, minus the non taxable amount, by the scale or
        the rate, minus what was already withheld this month. Other regimes: the rate, unless the payment or the
        base do not reach their minimum. In both cases the amount is 0 below the minimum withholding.
        """
        self.ensure_one()
        tax = self.tax_id
        company_currency = self.comodel_company_currency_id
        base_amount = company_currency.round(self.base_amount / self._l10n_ar_get_company_to_line_rate())
        f = company_currency.format
        ref = False

        if tax.l10n_ar_withholding_tax_type in EARNINGS_TAX_TYPES:
            accumulation = self.payment_id.partner_id._l10n_ar_get_period_accumulation(
                tax=tax, date=self.comodel_date, exclude_payment=self.payment_id._origin
            )
            same_period_base, same_period_withheld = accumulation["base"], accumulation["withheld"]
            net_amount = max(0, base_amount + same_period_base - tax.l10n_ar_non_taxable_amount)
            if net_amount <= 0:
                ref = f"{f(base_amount)} + {f(same_period_base)} - {f(tax.l10n_ar_non_taxable_amount)} = {f(base_amount + same_period_base - tax.l10n_ar_non_taxable_amount)} (no corresponde aplicar)"
            if tax.l10n_ar_withholding_tax_type == "earnings_scale":
                if not tax.l10n_ar_scale_id:
                    raise RedirectWarning(
                        _(
                            "Withholding tax '%s' (id: %s) is of type earnings scale but has no scale defined (field l10n_ar_scale_id). Please define a scale in the tax configuration."
                        )
                        % (tax.name, tax.id),
                        {
                            "view_mode": "form",
                            "res_model": "account.tax",
                            "type": "ir.actions.act_window",
                            "res_id": tax.id,
                            "views": [[False, "form"]],
                        },
                        _("Configure tax"),
                    )
                tax_amount = tax.l10n_ar_scale_id._l10n_ar_get_tax_amount_from_bracket(net_amount)
                bracket = self._l10n_ar_get_scale_bracket(net_amount)
                ref = (
                    ref
                    or f"({f(base_amount)} + {f(same_period_base)} - {f(tax.l10n_ar_non_taxable_amount)} - {f(bracket.from_amount)}) * {bracket.percentage}% + {f(bracket.fixed_amount)} - {f(same_period_withheld)}"
                )
            else:
                tax_amount = self._l10n_ar_apply_withholding_tax(
                    custom_base_amount=net_amount, currency=company_currency
                )
                ref = f"({f(base_amount)} + {f(same_period_base)} - {f(tax.l10n_ar_non_taxable_amount)}) * {abs(tax.amount)}% - {f(same_period_withheld)}"
            tax_amount -= same_period_withheld
        else:
            # Gates por pago y por base, en el orden normativo definido en la spec.
            if (
                tax.l10n_ar_payment_minimum_threshold
                and self.payment_id.to_pay_amount <= tax.l10n_ar_payment_minimum_threshold
            ):
                return 0.0, False
            if tax.l10n_ar_base_minimum_threshold and base_amount <= tax.l10n_ar_base_minimum_threshold:
                return 0.0, False
            tax_amount = self._l10n_ar_apply_withholding_tax(custom_base_amount=base_amount, currency=company_currency)

        if tax.l10n_ar_minimum_threshold > tax_amount:
            tax_amount = 0.0
        return tax_amount, ref

    def _l10n_ar_get_scale_bracket(self, net_amount):
        """Bracket of the scale used for net_amount, the same one _l10n_ar_get_tax_amount_from_bracket picks."""
        lines = self.tax_id.l10n_ar_scale_id.line_ids
        bracket = lines.filtered(lambda line: line.from_amount <= net_amount < line.to_amount)[:1]
        if not bracket:
            highest_bracket = lines.sorted("to_amount")[-1:]
            if net_amount >= highest_bracket.to_amount:
                bracket = highest_bracket
        return bracket

    @api.constrains("base_amount")
    def _constrains_base_amount(self):
        # A draft payment pro payment proposes its lines before the debt is selected, so the base can still be 0:
        # lines without withholding are dropped when posting.
        computable = self._l10n_ar_get_computable_withholdings().filtered(
            lambda x: x.comodel_currency_id.is_zero(x.base_amount)
        )
        return super(AccountPaymentWithholdingLine, self - computable)._constrains_base_amount()

    def _get_withholding_tax(self):
        """Return the applicable withheld tax (used by the AR exports)."""
        self.ensure_one()
        return self.tax_id

    ########################
    # EARNING COMPUTE HELPERS
    ########################

    def _get_same_period_withholdings_domain(self):
        """Posted earnings withholding lines of the same regime and commercial partner, from the first day of the
        month to the date of the payment."""
        self.ensure_one()
        to_date = self.payment_id.date or fields.Date.context_today(self)
        from_date = to_date + relativedelta(day=1)
        return [
            # same legal entity as the accumulation (account_ux), on company_id like any company domain
            *self.env["account.move.line"]._check_company_domain(self.tax_id.company_id),
            ("payment_id.state", "in", ["paid", "reconciled"]),
            ("tax_id.l10n_ar_code", "=", self.tax_id.l10n_ar_code),
            ("tax_id.l10n_ar_withholding_tax_type", "in", list(EARNINGS_TAX_TYPES)),
            ("payment_id.partner_id.commercial_partner_id", "=", self.payment_id.partner_id.commercial_partner_id.id),
            ("payment_id.date", "<=", to_date),
            ("payment_id.date", ">=", from_date),
        ]

    ##########
    # ACTIONS
    ##########

    def action_l10n_ar_payment_withholding_tree(self):
        """Open a list view showing previous withholdings."""
        return {
            "name": _("Previous Withholdings"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment.withholding.line",
            "view_mode": "list",
            "view_id": self.env.ref("l10n_ar_tax.view_l10n_ar_payment_withholding_tree").id,
            "domain": self._get_same_period_withholdings_domain(),
        }
