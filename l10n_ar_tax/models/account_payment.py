##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import column_exists, create_column


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # source string of the core message, to find it among the ones the core returns without reading a translation
    MISMATCH_CHECK_AMOUNT_MSG = (
        "The amount of the payment  does not match the amount of the selected check. "
        "Please try to deselect and select the check again."
    )

    withholding_line_ids = fields.One2many(
        compute="_compute_withholding_line_ids",
        store=True,
        readonly=False,
    )
    l10n_ar_fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Fiscal Position",
        check_company=True,
        compute="_compute_fiscal_position_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', l10n_ar_allowed_fiscal_position_ids)]",
    )
    l10n_ar_allowed_fiscal_position_ids = fields.Many2many(
        "account.fiscal.position",
        string="Allowed Fiscal Positions",
        compute="_compute_l10n_ar_allowed_fiscal_position_ids",
    )

    # amount is the gross amount (paid + withheld); the user works with the net one, as in 19.0
    withhold = fields.Selection(compute="_compute_withhold", store=True, readonly=False)
    withholding_net_amount = fields.Monetary(readonly=False, inverse="_inverse_withholding_net_amount")
    withholding_net_amount_signed = fields.Monetary(
        string="Net Amount in Currency",
        currency_field="currency_id",
        compute="_compute_withholding_net_amount_signed",
    )
    counterpart_currency_net_amount = fields.Monetary(
        string="Net Amount in Debt Currency",
        currency_field="counterpart_currency_id",
        compute="_compute_counterpart_currency_net_amount",
        inverse="_inverse_counterpart_currency_net_amount",
        readonly=False,
    )
    destination_currency_withholding_amount = fields.Monetary(
        string="Withholdings",
        currency_field="destination_currency_id",
        compute="_compute_destination_currency_withholding_amount",
        help="Withholdings in the debt currency, at the rate of the payment.",
    )
    # Round-trip of the onchange, to know how much the withholdings changed.
    previous_withholding_amount = fields.Monetary(
        currency_field="currency_id",
        store=True,
        copy=False,
    )

    def _auto_init(self):
        # create the columns by hand so that installing does not queue a recompute over the whole
        # payment history: on a big database that sweep goes over the worker time limit and the
        # install dies half way through
        if not column_exists(self.env.cr, "account_payment", "l10n_ar_fiscal_position_id"):
            # left empty on purpose: only draft supplier payments end up with one, and those are
            # computed from _l10n_ar_update_taxes
            create_column(self.env.cr, "account_payment", "l10n_ar_fiscal_position_id", "int4")
        if not column_exists(self.env.cr, "account_payment", "withholdable_advanced_amount"):
            # DEFAULT 0 fills the existing rows without rewriting the table (postgres keeps it as
            # metadata), so they hold the same 0.0 the compute would have stored. Leaving them NULL
            # reads as 0.0 too, but is not matched by a `= 0` domain. The default is dropped right
            # away so the column ends up exactly as the ORM would have created it
            self.env.cr.execute("ALTER TABLE account_payment ADD COLUMN withholdable_advanced_amount numeric DEFAULT 0")
            self.env.cr.execute("ALTER TABLE account_payment ALTER COLUMN withholdable_advanced_amount DROP DEFAULT")
            # only the payments carrying an advance need the backfill. It is not narrowed to the
            # draft ones: unreconciled_amount does not change when a payment is reset to draft, so
            # the compute would never fill them again
            self.env.cr.execute(
                "UPDATE account_payment SET withholdable_advanced_amount = unreconciled_amount"
                " WHERE unreconciled_amount <> 0"
            )
        return super()._auto_init()

    @api.depends("company_id")
    def _compute_l10n_ar_allowed_fiscal_position_ids(self):
        FiscalPosition = self.env["account.fiscal.position"]
        for rec in self:
            rec.l10n_ar_allowed_fiscal_position_ids = FiscalPosition._l10n_ar_withholding_positions_for(rec.company_id)

    @api.depends("to_pay_move_line_ids", "partner_id", "payment_method_line_id")
    def _compute_fiscal_position_id(self):
        for rec in self:
            # a non draft payment keeps its fiscal position: it is the one its withholdings were computed with
            if rec.state != "draft":
                continue
            if (
                rec.partner_type != "supplier"
                or rec.country_code != "AR"
                or not rec.use_payment_pro
                or self.env.context.get("create_and_new")
            ):
                rec.l10n_ar_fiscal_position_id = False
                continue
            # si estamos pagando todas las facturas de misma delivery address usamos este dato para computar la
            # fiscal position
            addresses = rec.to_pay_move_line_ids.mapped("move_id.partner_shipping_id")
            if len(addresses) == 1:
                address = addresses
            else:
                address = rec.partner_id
            rec.l10n_ar_fiscal_position_id = (
                self.env["account.fiscal.position"]
                .with_company(rec.company_id)
                .with_context(l10n_ar_withholding=True)
                ._get_fiscal_position(address)
            )

    @api.constrains("withholding_line_ids", "partner_id")
    def _check_partner_for_withholdings(self):
        for rec in self.filtered(lambda x: x.country_code == "AR"):
            if rec.withholding_line_ids and not rec.partner_id:
                raise ValidationError(_("Partner must be set on the payment to compute withholdings"))

    def _get_withholding_rate(self):
        """Tasa efectiva B->C para convertir base de retención a ARS.
        Devuelve multiplicador directo: base_in_B * rate = base_in_C.
        Ejemplo: B=USD, C=ARS, rate=1200 -> 100 USD * 1200 = 120.000 ARS.

        Usa las tasas configuradas en el pago (no la tasa spot) para respetar
        ediciones manuales del usuario. Fórmula: C/B = (C/A) * (A/B)
        = (1/accounting_rate) / counterpart_rate.
        """
        self.ensure_one()
        if not self.destination_currency_id or self.destination_currency_id == self.company_currency_id:
            return 1.0
        accounting = self.accounting_rate or 1.0  # A/C
        counterpart = self.counterpart_rate or 1.0  # B1/A (B1 ≈ B en casos típicos)
        # C/B = (C/A) * (A/B) = (1/accounting_rate) * (1/counterpart_rate)
        return (1.0 / accounting) / counterpart

    ###################################################
    # el importe neto: lo que el usuario tipea y lee
    ###################################################

    @api.depends("withholding_line_ids.amount")
    def _compute_amount(self):
        """Only to declare the dependency: what the withholdings move lives in _adjust_computed_amount, which
        payment pro calls before syncing amount_exact."""
        super()._compute_amount()

    def _adjust_computed_amount(self):
        """EXTENDS account_payment_pro: with withholdings the amount of a check payment is not the one the core
        computes."""
        super()._adjust_computed_amount()
        # the checks are the net amount: the gross one adds the withholdings
        for rec in self.filtered(
            lambda x: x.state == "draft" and x._is_latam_check_payment() and x.withholding_line_ids
        ):
            # the lines, and not the withholding_amount they add up to: this compute declares them as its
            # dependency, so the total may still be the old one while they are being recomputed
            rec.amount = rec.l10n_latam_checks_amount + sum(rec.withholding_line_ids.mapped("amount"))
        # out of the draft state the amount is the one the payment was confirmed with: action_post numbers the
        # withholdings, and that write on the one2many fires this compute again, where the checks leave the
        # amount at the net one
        for rec in self.filtered(
            lambda x: x.state != "draft" and x._is_latam_check_payment() and x.withholding_line_ids and x.amount_exact
        ):
            rec.amount = rec.amount_exact

    @api.depends("use_payment_pro", "withholding_amount", "amount")
    def _compute_withhold(self):
        """With payment pro the mode follows the withholding lines instead of being chosen by the user."""
        for rec in self:
            if not rec.use_payment_pro:
                rec.withhold = rec.withhold or "payment"
            elif not rec.withholding_line_ids:
                rec.withhold = "payment"
            elif rec.currency_id.is_zero(rec.amount - rec.withholding_amount):
                rec.withhold = "withhold"
            else:
                rec.withhold = "withhold_pay"

    @api.onchange("withholding_net_amount")
    def _onchange_withholding_net_amount(self):
        """The onchange lives apart from the inverse: the registry takes the last method of the MRO, so a module
        overriding the inverse would leave the field without an onchange."""
        self._inverse_withholding_net_amount()

    def _inverse_withholding_net_amount(self):
        for rec in self:
            amount = rec.withholding_net_amount + rec.withholding_amount
            if rec.currency_id and not rec.currency_id.is_zero(amount - rec.amount):
                rec.amount_exact = amount
                rec.amount = amount

    @api.depends("withholding_net_amount", "payment_type")
    def _compute_withholding_net_amount_signed(self):
        for rec in self:
            sign = -1 if rec.payment_type == "outbound" else 1
            rec.withholding_net_amount_signed = sign * rec.withholding_net_amount

    def _get_withholding_amount_in(self, currency, rate):
        """Withholdings in ``currency``, ``rate`` being its units per unit of the payment currency.

        In company currency they are the amounts the entry books: a line in a foreign currency is not
        rounded back through it, so the header and the entry show the same withholdings.
        """
        self.ensure_one()
        company_currency = self.company_currency_id
        if currency == company_currency and self.currency_id != company_currency and self.accounting_rate:
            return sum(line._get_company_currency_amounts()["amount"] for line in self.withholding_line_ids)
        return self.withholding_amount * rate

    @api.depends(
        "counterpart_currency_amount",
        "withholding_amount",
        "counterpart_rate",
        "accounting_rate",
        "counterpart_currency_id",
    )
    def _compute_counterpart_currency_net_amount(self):
        for rec in self:
            withholding = rec._get_withholding_amount_in(rec.counterpart_currency_id, rec.counterpart_rate or 1.0)
            rec.counterpart_currency_net_amount = rec.counterpart_currency_amount - withholding

    @api.depends(
        "withholding_amount",
        "counterpart_rate",
        "accounting_rate",
        "counterpart_currency_id",
        "destination_currency_id",
    )
    def _compute_destination_currency_withholding_amount(self):
        # same A -> B2 conversion as _compute_payment_total
        for rec in self:
            if rec.counterpart_currency_id != rec.destination_currency_id:
                rate = 1.0 / rec.accounting_rate if rec.accounting_rate else 1.0
            else:
                rate = rec.counterpart_rate or 1.0
            rec.destination_currency_withholding_amount = rec._get_withholding_amount_in(
                rec.destination_currency_id, rate
            )

    @api.onchange("counterpart_currency_net_amount")
    def _onchange_counterpart_currency_net_amount(self):
        """The onchange lives apart from the inverse, for the same reason as the counterpart amount one."""
        self._inverse_counterpart_currency_net_amount()

    def _inverse_counterpart_currency_net_amount(self):
        for rec in self:
            withholding = rec._get_withholding_amount_in(rec.counterpart_currency_id, rec.counterpart_rate or 1.0)
            gross = rec.counterpart_currency_net_amount + withholding
            if rec.counterpart_currency_id and not rec.counterpart_currency_id.is_zero(
                gross - rec.counterpart_currency_amount
            ):
                rec.counterpart_currency_amount = gross
                rec._inverse_counterpart_currency_amount()

    @api.depends("withholding_line_ids.amount", "accounting_rate")
    def _compute_amount_company_currency_signed(self):
        """Without an entry the core converts the gross amount; what goes through the bank is the net one,
        which is also what the posted payment shows (its liquidity lines)."""
        super()._compute_amount_company_currency_signed()
        for rec in self.filtered(lambda x: not x.move_id and x.use_payment_pro and x.withholding_line_ids):
            if rec.accounting_rate and rec.currency_id != rec.company_currency_id:
                amount = rec.withholding_net_amount_signed / rec.accounting_rate
            else:
                amount = rec.currency_id._convert(
                    rec.withholding_net_amount_signed, rec.company_currency_id, rec.company_id, rec.date
                )
            rec.amount_company_currency_signed = rec.company_currency_id.round(amount)

    def _get_blocking_l10n_latam_warning_msg(self):
        """The core compares the checks with the payment amount, but with withholdings they pay the net one."""
        mismatch_msg = _(
            "The amount of the payment  does not match the amount of the selected check. "
            "Please try to deselect and select the check again."
        )
        msgs = super()._get_blocking_l10n_latam_warning_msg()
        with_withholdings = self.filtered(
            lambda x: x.state == "draft" and x._is_latam_check_payment() and x.withholding_line_ids
        )
        if not with_withholdings:
            return msgs
        # the core message is dropped by its position, never by its text: each module translates the same source
        # string with its own catalog, so comparing the translated ones only matches in English. Both calls run
        # over the same records and build the list the same way, so the two are aligned.
        source_msgs = super(AccountPayment, self.with_context(lang="en_US"))._get_blocking_l10n_latam_warning_msg()
        msgs = [msg for msg, source in zip(msgs, source_msgs) if source != self.MISMATCH_CHECK_AMOUNT_MSG]
        for rec in self.filtered(lambda x: x.state == "draft" and x._is_latam_check_payment()):
            checks_amount = sum(rec._get_latam_checks().mapped("amount"))
            if not rec.currency_id.is_zero(checks_amount - rec.withholding_net_amount):
                msgs.append(mismatch_msg)
        return msgs

    @api.onchange("withholding_amount")
    def _onchange_withholding_amount(self):
        """Single onchange of the field: the previous total is booked once and each payment takes its branch, so
        the result does not depend on the order the methods are defined in."""
        for rec in self:
            delta = rec.withholding_amount - rec.previous_withholding_amount
            rec.previous_withholding_amount = rec.withholding_amount
            if rec.partner_type == "supplier":
                rec._follow_selected_debt()
            else:
                rec._keep_typed_net_amount(delta)

    def _follow_selected_debt(self):
        """When the withholdings change (the selected debt, its base, or the partner changed), the gross amount
        follows the selected debt, up and down and never below zero. Supplier payments only, and not with third
        party checks already selected, where the checks set the amount."""
        third_party_checks = (
            "in_third_party_checks",
            "out_third_party_checks",
            "return_third_party_checks",
            "new_third_party_checks",
        )
        for rec in self.filtered(
            lambda x: x.use_payment_pro
            and x.state == "draft"
            and x.partner_type == "supplier"
            and x.currency_id
            and (x.payment_method_code not in third_party_checks or not x._get_latam_checks())
        ):
            amount = max(rec.amount + rec._get_payment_difference_in_currency_a(), 0.0)
            if not rec.currency_id.is_zero(amount - rec.amount):
                rec.amount = amount
                rec.amount_exact = amount

    def _keep_typed_net_amount(self, delta):
        """Outside a supplier payment the net the user typed stays put: the gross follows the withholdings and
        the difference shows up as the adjustment to make, as in 19.0, where the amount was the net one and
        ``_onchange_withholdings`` of l10n_ar_tax only moved it on supplier payments."""
        self.ensure_one()
        if not self.use_payment_pro or self.state != "draft":
            return
        if not self.currency_id or self.currency_id.is_zero(delta):
            return
        amount = max(self.amount + delta, 0.0)
        self.amount = amount
        self.amount_exact = amount

    @api.onchange("partner_id")
    def _onchange_partner_id_follow_debt(self):
        """A new partner brings its own debt: the amount follows it, as when the withholdings change."""
        self.filtered(lambda x: x.partner_id != x._origin.partner_id)._follow_selected_debt()

    def _on_currency_changed(self, old_currency):
        """EXTENDS account_payment_pro: the withholding lines are in the payment currency as well, and they follow
        the rate of the payment (the one the entry books, which the user can type) and not the one of the day."""
        super()._on_currency_changed(old_currency)
        for rec in self:
            old_rate = rec._get_accounting_rate_for(old_currency)
            new_rate = rec.accounting_rate
            if not old_rate or not new_rate:
                continue
            for line in rec.withholding_line_ids:
                line.update(
                    {
                        "base_amount": rec.currency_id.round(line.base_amount / old_rate * new_rate),
                        "amount": rec.currency_id.round(line.amount / old_rate * new_rate),
                    }
                )

    def _books_no_liquidity_line(self):
        """EXTENDS account_payment_pro: a withholding-only payment has no liquidity line."""
        return self.withhold == "withhold" or super()._books_no_liquidity_line()

    def action_amount_from_checks(self):
        """EXTENDS account_payment_pro: the checks are the net amount, so the gross one adds the withholdings."""
        super().action_amount_from_checks()
        for rec in self.filtered(lambda x: x.state == "draft" and x._is_latam_check_payment()):
            rec.amount += rec.withholding_amount

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_previous_withholding_amount()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "withholding_line_ids" in vals and "previous_withholding_amount" not in vals:
            self._sync_previous_withholding_amount()
        return res

    def _sync_previous_withholding_amount(self):
        """The onchange reads it to know how much the withholdings moved, so a saved record carries the real total
        even when it was not created through the form."""
        for rec in self:
            if rec.currency_id and not rec.currency_id.is_zero(
                rec.withholding_amount - rec.previous_withholding_amount
            ):
                rec.previous_withholding_amount = rec.withholding_amount

    def _l10n_ar_remove_zero_withholding_lines(self):
        """Elimina las líneas de retención que no arrojan retención (importe 0) al postear
        el pago, para que no queden en el pago ni ensucien la vista/reportes.
        Ganancias se conserva siempre: su base acumulada puede requerir el apunte contable
        aunque el importe sea 0. Usamos ``currency_id.is_zero`` (mismo criterio que
        account_tax_settlement al saltear líneas en cero) para contemplar el redondeo."""
        for rec in self.filtered(lambda x: x.country_code == "AR"):
            is_zero = rec.currency_id.is_zero
            zero_lines = rec.withholding_line_ids.filtered(
                lambda line: line.tax_id.l10n_ar_withholding_tax_type not in ["earnings", "earnings_scale"]
                and is_zero(line.amount)
            )
            if zero_lines:
                rec.withholding_line_ids = [Command.unlink(line.id) for line in zero_lines]

    def action_post(self):
        self._l10n_ar_remove_zero_withholding_lines()
        for rec in self.filtered(lambda x: x.country_code == "AR"):
            commands = []
            for line in rec.withholding_line_ids:
                if not line.name or line.name == "/":
                    if line.tax_id.withholding_sequence_id:
                        commands.append(
                            Command.update(
                                line.id,
                                {"name": line.tax_id.withholding_sequence_id.next_by_id() if line.amount else "/"},
                            )
                        )
                    else:
                        raise UserError(
                            _("Please enter withholding number for tax %s or configure a sequence on its tax group")
                            % line.tax_id.name
                        )
            if commands:
                rec.withholding_line_ids = commands

        return super().action_post()

    def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        """The entry carries the withholding lines as the payment computed them. Without skipping the dynamic sync, it
        rebuilds them from the tax engine: a line that withholds 0 (earnings under the non taxable amount) gets a tax
        line by its plain rate, and an amount typed by the user goes back to the rate."""
        wth_payments = self.filtered(lambda x: x.country_code == "AR" and x.withholding_line_ids)
        if wth_payments:
            super(AccountPayment, wth_payments.with_context(skip_invoice_sync=True))._generate_journal_entry(
                write_off_line_vals, force_balance, line_ids
            )
        return super(AccountPayment, self - wth_payments)._generate_journal_entry(
            write_off_line_vals, force_balance, line_ids
        )

    def action_draft(self):
        # The supplier payment receipt PDF is cached (attachment_use on
        # account.report_payment_receipt). Resetting to draft means the payment
        # may be edited (amounts, withholdings, reconciliation) and reposted
        # under the same name, which would otherwise serve the stale cached PDF.
        # Drop the cached receipt so it is regenerated on the next render.
        self._unlink_cached_payment_receipt()
        self._unlink_cached_withholding_certificates()
        return super().action_draft()

    def _l10n_ar_withholding_certificates_filename(self):
        """Filename of the single PDF holding all the withholding certificates
        of this payment (one page per withholding). Shared by the preview and
        the sending path of mail.compose.message."""
        self.ensure_one()
        return "Certificados de Retención - %s.pdf" % (self.name or "").replace("/", "_")

    def _unlink_cached_withholding_certificates(self):
        # Same rationale as _unlink_cached_payment_receipt: the certificate of
        # each withholding line is cached (attachment_use on
        # l10n_ar_tax.action_report_withholding_certificate) and becomes stale
        # if the payment is edited and reposted under the same name.
        report = self.env.ref("l10n_ar_tax.action_report_withholding_certificate", raise_if_not_found=False)
        if not report:
            return
        for withholding in self.withholding_line_ids:
            attachment = report.retrieve_attachment(withholding)
            if attachment:
                attachment.unlink()

    def _unlink_cached_payment_receipt(self):
        report = self.env.ref("account.action_report_payment_receipt", raise_if_not_found=False)
        if not report:
            return
        for payment in self:
            # retrieve_attachment evalúa la misma expresión `attachment` del
            # reporte (devuelve None si no corresponde cachear, p.ej. clientes).
            attachment = report.retrieve_attachment(payment)
            if attachment:
                attachment.unlink()

    ###################################################
    # desde account_withholding_automatic payment.group
    ###################################################

    withholdable_advanced_amount = fields.Monetary(
        "Adjustment / Advance (untaxed)",
        help="Used for withholdings calculation",
        currency_field="destination_currency_id",
        compute="_compute_withholdable_advanced_amount",
        copy=False,
        store=True,
        readonly=False,
    )
    selected_debt_untaxed = fields.Monetary(
        # string='To Pay lines Amount',
        compute="_compute_selected_debt_untaxed",
        currency_field="destination_currency_id",
    )
    matched_amount_untaxed = fields.Monetary(
        compute="_compute_matched_amount_untaxed",
        currency_field="currency_id",
    )

    def _compute_matched_amount_untaxed(self):
        """Lo separamos en otro metodo ya que es un poco mas costoso y no se
        usa en conjunto con matched_amount
        """
        for rec in self:
            rec.matched_amount_untaxed = 0.0
            if rec.state != "posted":
                continue
            matched_amount_untaxed = 0.0
            sign = rec.payment_type == "outbound" and -1.0 or 1.0
            for line in rec.matched_move_line_ids.with_context(matched_payment_ids=rec.ids):
                invoice = line.move_id
                factor = invoice and invoice._get_tax_factor() or 1.0
                # TODO implementar
                matched_amount_untaxed += line.payment_matched_amount * factor
            rec.matched_amount_untaxed = sign * matched_amount_untaxed

    @api.depends("to_pay_move_line_ids", "destination_currency_id", "company_currency_id", "payment_type")
    def _compute_selected_debt_untaxed(self):
        for rec in self:
            selected_debt_untaxed = 0.0
            for line in rec.to_pay_move_line_ids._origin:
                factor = line.move_id._get_tax_factor() if line.move_id else 1.0
                if rec.destination_currency_id and rec.destination_currency_id != rec.company_currency_id:
                    selected_debt_untaxed += line.amount_residual_currency * factor
                else:
                    selected_debt_untaxed += line.amount_residual * factor
            rec.selected_debt_untaxed = selected_debt_untaxed * (-1.0 if rec.payment_type == "outbound" else 1.0)

    @api.depends("unreconciled_amount")
    def _compute_withholdable_advanced_amount(self):
        for rec in self:
            rec.withholdable_advanced_amount = rec.unreconciled_amount

    def _l10n_ar_proposes_withholdings(self):
        """Payments whose withholdings we propose from the fiscal position: draft supplier payment pro payments of AR.
        The rest keep the lines they have (entered by hand, or the ones of a posted payment)."""
        self.ensure_one()
        return (
            self.state == "draft"
            and self.partner_type == "supplier"
            and self.country_code == "AR"
            and self.use_payment_pro
        )

    @api.depends("l10n_ar_fiscal_position_id", "partner_id", "company_id", "date")
    def _compute_withholding_line_ids(self):
        # no entiendo porque pero acá viene un active_test=False que se termina propagando a computed fields que
        # también dependan de partner_id, por ahora forzamos active_test=True para que aguas arriba todo se compute bien
        for rec in self.with_context(active_test=True):
            if not rec._l10n_ar_proposes_withholdings():
                rec.withholding_line_ids = rec.withholding_line_ids
                continue
            date = rec.date or fields.Date.context_today(rec)
            withholdings = [Command.clear()]
            if rec.l10n_ar_fiscal_position_id.l10n_ar_tax_ids:
                taxes = rec.l10n_ar_fiscal_position_id._l10n_ar_add_taxes(
                    rec.partner_id, rec.company_id, date, "withholding", rec
                )
                withholdings += [Command.create({"tax_id": x.id}) for x in taxes]
            rec.withholding_line_ids = withholdings

    def compute_to_pay_amount_for_check(self):
        checks_payments = self.filtered(
            lambda x: x.payment_method_code in ["in_third_party_checks", "out_third_party_checks"]
        )
        for rec in checks_payments.with_context(skip_account_move_synchronization=True):
            # dejamos 230 porque el hecho de estar usando valor de "$2" abajo y subir de a un centavo hace podamos necesitar
            # 200 intento solo en esa seccion
            # deberiamos ver de ir aproximando de otra manera
            remining_attemps = 230
            while not rec.currency_id.is_zero(rec.payment_difference):
                if remining_attemps == 0:
                    raise UserError(
                        _(
                            'Maximum attempts reached. Could not compute the amount to pay. The last amount we reached was "%s"'
                        )
                        % rec.to_pay_amount
                    )
                remining_attemps -= 1
                # el payment difference es negativo, para entenderlo mejor lo pasamos a postivo
                # por ahora, arbitrariamente, si la diferencia es mayor a 2 vamos sumando la payment difference
                # para llegar mas rapido al numero
                # cuando ya estamos cerca del numero empezamos a sumar de a 1 centavo.
                # no lo hacemos siempre sumando el difference porque podria ser que por temas de redondeo o escalamiento
                # nos pasemos del otro lado
                # TODO ver si conviene mejor hacer una ponderacion porcentual
                if -rec.payment_difference > 2:
                    rec.to_pay_amount -= rec.payment_difference
                elif -rec.payment_difference > 0:
                    rec.to_pay_amount += 0.01
                elif rec.to_pay_amount > rec.amount:
                    # este caso es por ej. si el cliente ya habia pre-completado con un to_pay_amount mayor al amount
                    # del pago
                    rec.to_pay_amount = 0.0
                else:
                    raise UserError(
                        "Hubo un error al querer computar el importe a pagar. Llegamos a estos valores:\n"
                        "* to_pay_amount: %s\n"
                        "* payment_difference: %s\n"
                        "* amount: %s" % (rec.to_pay_amount, rec.payment_difference, rec.amount)
                    )
            rec.with_context(skip_account_move_synchronization=False)._synchronize_to_moves({"withholding_line_ids"})

    def _get_bundle_payment_total(self, payment_bundle):
        """Total to display in the bundled receipt 'Total Paid' footer.
        Sums payment_total across all payments in the bundle.
        Override in modules where the first payment already aggregates the rest (e.g. l10n_ar_payment_bundle).
        """
        return sum(payment_bundle.mapped("payment_total"))

    def _get_bundle_imputed_total(self, payment_bundle):
        """Total to display in the bundled receipt 'Total Imputed' footer."""
        return sum(payment_bundle.mapped("matched_amount")) + sum(payment_bundle.mapped("unmatched_amount"))

    def _get_name_receipt_report(self, report_xml_id):
        """Method similar to the '_get_name_invoice_report' of l10n_latam_invoice_document
        Basically it allows different localizations to define it's own report
        This method should actually go in a sale_ux module that later can be extended by different localizations
        Another option would be to use report_substitute module and setup a subsitution with a domain
        """
        self.ensure_one()
        if self.company_id.country_id.code == "AR" and not self.is_internal_transfer:
            return "l10n_ar_tax.report_payment_receipt_document"
        return super()._get_name_receipt_report(report_xml_id)

    def _get_payment_bundle_key(self):
        if self.company_id.country_id.code == "AR" and self.env.context.get("print_in_bundles"):
            return f"{self.company_id.id}-{self.partner_id.id}-{self.payment_type}-{self.currency_id.id if self.currency_id != self.company_currency_id else self.counterpart_currency_id.id}"
        return super()._get_payment_bundle_key()

    def _compute_to_pay_move_lines(self):
        # When creating payments from the bulk payment wizard, we explicitly set
        # to_pay_move_line_ids to the selected lines only, so we skip auto-computation
        # to avoid _add_all() adding unrelated lines of different currencies.
        if self.env.context.get("skip_to_pay_compute"):
            return
        return super()._compute_to_pay_move_lines()
