from odoo import api, fields, models


class l10nArPaymentWithholding(models.Model):
    _inherit = "l10n_ar.payment.withholding"

    # The regime code in version 16.0 is available in the payment.group model,
    # and in version 17, it's located in account.payment.
    regime_code = fields.Char(
        readonly=True,
    )
    regime_tax_id = fields.Many2one("account.tax", compute="_compute_regime_tax_id", store=True)

    @api.depends("company_id", "regime_code", "payment_id.is_backward_withholding_payment")
    def _compute_regime_tax_id(self):
        """Computamos el valor de regime_code y seteamos regime_tax_id con el impuesto
        Activo que tiene ese regimen en el campo l10n_ar_code
        TODO: Deberiamos buscar con active_test False ¿puede haber mas de un
        impuesto con el mismo l10n_ar_code que este activo y desactivado?
        """
        for company in self.mapped("company_id"):
            backward_lines_ids = self.filtered(
                lambda x: x.payment_id.is_backward_withholding_payment and x.company_id == company
            )
            if backward_lines_ids:
                regime_codes = backward_lines_ids.filtered("regime_code").mapped("regime_code")
                if regime_codes:
                    tax_by_codes = {
                        x.l10n_ar_code: x
                        for x in self.env["account.tax"].search(
                            [("company_id", "=", company.id), ("l10n_ar_code", "in", regime_codes)]
                        )
                    }
                    for line in backward_lines_ids:
                        line.regime_tax_id = tax_by_codes.get(line.regime_code, False)
                        self -= line
        self.regime_tax_id = False

    # These fields are used in previous versions that
    # We use this to calculating accumulated amounts
    # in addition as backup and reference

    automatic = fields.Boolean()
    withholdable_invoiced_amount = fields.Monetary(
        "Importe imputado sujeto a retencion",
        readonly=True,
    )
    withholdable_advanced_amount = fields.Monetary(
        "Importe a cuenta sujeto a retencion",
    )
    accumulated_amount = fields.Monetary(
        readonly=True,
    )
    total_amount = fields.Monetary(
        readonly=True,
    )
    withholding_non_taxable_minimum = fields.Monetary(
        "Non-taxable Minimum",
        readonly=True,
    )
    withholding_non_taxable_amount = fields.Monetary(
        "Non-taxable Amount",
        readonly=True,
    )
    withholdable_base_amount = fields.Monetary(
        readonly=True,
    )
    period_withholding_amount = fields.Monetary(
        readonly=True,
    )
    previous_withholding_amount = fields.Monetary(
        readonly=True,
    )
    computed_withholding_amount = fields.Monetary(
        readonly=True,
    )

    ########################
    # EARNING COMPUTE HELPERS
    ########################

    def _get_withholding_tax(self):
        """If payment is a backward withholding payment the applied tax is regime_tax_id"""
        self.ensure_one()
        if self.payment_id.is_backward_withholding_payment and self.regime_tax_id:
            return self.regime_tax_id
        return super()._get_withholding_tax()

    def _get_same_period_withholdings_domain(self):
        """Avoid compute backward payments two times"""
        return super()._get_same_period_withholdings_domain() + [
            ("payment_id.is_backward_withholding_payment", "=", False)
        ]

    def _get_same_period_base_domain(self):
        """Avoid compute bases backward payments two times"""
        return super()._get_same_period_base_domain() + [("payment_id.is_backward_withholding_payment", "=", False)]

    def _get_same_period_withholdings_amount(self):
        amount = super()._get_same_period_withholdings_amount()
        to_date, from_date = self._get_same_period_dates()
        tax_id = self._get_withholding_tax()

        domain_same_period_withholdings = [
            *self._check_company_domain(tax_id.company_id),
            ("payment_id.state", "in", ["paid", "posted"]),
            ("payment_id.is_backward_withholding_payment", "=", True),
            ("regime_tax_id.l10n_ar_code", "=", tax_id.l10n_ar_code),
            ("regime_tax_id.l10n_ar_tax_type", "in", ["earnings", "earnings_scale"]),
            ("payment_id.partner_id.commercial_partner_id", "=", self.payment_id.partner_id.commercial_partner_id.id),
            ("payment_id.date", "<=", to_date),
            ("payment_id.date", ">=", from_date),
        ]

        if same_period_partner_withholdings := self._read_group(
            domain_same_period_withholdings, ["company_id"], ["amount:sum"]
        ):
            amount += abs(same_period_partner_withholdings[0][1])
        return amount

    def _get_same_period_base_amount(self):
        self.ensure_one()
        amount = super()._get_same_period_base_amount()
        to_date, from_date = self._get_same_period_dates()
        tax_id = self._get_withholding_tax()
        domain_same_period_base = [
            *self._check_company_domain(tax_id.company_id),
            ("payment_id.state", "in", ["paid", "posted"]),
            ("payment_id.is_backward_withholding_payment", "=", True),
            ("regime_tax_id.l10n_ar_code", "=", tax_id.l10n_ar_code),
            ("regime_tax_id.l10n_ar_tax_type", "in", ["earnings", "earnings_scale"]),
            ("payment_id.partner_id.commercial_partner_id", "=", self.payment_id.partner_id.commercial_partner_id.id),
            ("payment_id.date", "<=", to_date),
            ("payment_id.date", ">=", from_date),
        ]
        if same_period_partner_base := self._read_group(domain_same_period_base, ["company_id"], ["base_amount:sum"]):
            amount += abs(same_period_partner_base[0][1])
        return amount
