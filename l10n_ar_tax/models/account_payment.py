##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import column_exists, create_column


class AccountPayment(models.Model):
    _inherit = "account.payment"

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
        domain=[("l10n_ar_tax_ids.tax_type", "=", "withholding")],
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

    @api.depends("to_pay_move_line_ids", "partner_id", "payment_method_line_id")
    def _compute_fiscal_position_id(self):
        for rec in self:
            if (
                rec.state != "draft"
                or rec.partner_type != "supplier"
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
                            _("Please enter withholding number for tax %s or configure a sequence on that tax")
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
