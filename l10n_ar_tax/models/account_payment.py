##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_ar_withholding_line_ids = fields.One2many(
        "l10n_ar.payment.withholding",
        "payment_id",
        string="Withholdings Lines",
        compute="_compute_l10n_ar_withholding_line_ids",
        readonly=False,
        store=True,
    )
    withholdings_amount = fields.Monetary(
        compute="_compute_withholdings_amount",
        currency_field="company_currency_id",
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
    withholding_warning = fields.Boolean(compute="_compute_withholding_warning")

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
                # TODO revisar porque llega active_test=False acá
                .with_context(l10n_ar_withholding=True, active_test=True)
                ._get_fiscal_position(address)
            )

    @api.depends("l10n_ar_withholding_line_ids.amount")
    def _compute_withholdings_amount(self):
        for rec in self:
            rec.withholdings_amount = sum(rec.l10n_ar_withholding_line_ids.mapped("amount"))

    def _get_withholding_move_line_default_values(self):
        return {}

    @api.depends("l10n_ar_withholding_line_ids.amount")
    def _compute_payment_total(self):
        super()._compute_payment_total()
        for rec in self.filtered("l10n_ar_withholding_line_ids"):
            if (rec.payment_type == "outbound" and rec.partner_type == "customer") or (
                rec.payment_type == "inbound" and rec.partner_type == "supplier"
            ):
                sign = -1
            else:
                sign = 1
            rec.payment_total += sum(x * sign for x in rec.l10n_ar_withholding_line_ids.mapped("amount"))

    # por ahora no nos funciona computarlas, se duplica el importe. Igual conceptualemnte el onchange acá por ahí
    # está bien porque en realidad es una "sugerencia" actualizar el amount al usuario
    # @api.depends('withholdings_amount')
    # def _compute_amount(self):
    #     latam_checks = self.filtered(lambda x: x._is_latam_check_payment())
    #     super(AccountPayment, latam_checks)._compute_amount()
    #     for rec in (self - latam_checks):
    @api.onchange("withholdings_amount")
    def _onchange_withholdings(self):
        # solo queremos re-computar en pagos de proveedor
        for rec in self.filtered(
            lambda x: x.partner_type == "supplier"
            and x.payment_method_code
            not in [
                "in_third_party_checks",
                "out_third_party_checks",
                "return_third_party_checks",
                "new_third_party_checks",
            ]
        ):
            # el compute_withholdings o el _compute_withholdings?
            amount = rec.amount + rec.payment_difference
            # no pasamos a importes negativos (por ej. si se ponene retenciones grandes) porque es molesto
            # empieza a salir un raise que no deja editar cosas
            rec.amount = amount if amount > 0 else 0
            # rec.unreconciled_amount = rec.to_pay_amount - rec.selected_debt

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for rec in self:
            if rec.partner_id != rec._origin.partner_id:
                rec._onchange_withholdings()

    # # ver mensaje en commit
    # @api.onchange('to_pay_amount', 'withholdable_advanced_amount', 'partner_id')
    # def _onchange_to_pay_amount(self):
    #     # para muchas retenciones es necesario que el partner este seteado, solo calculamos si viene definido
    #     for rec in self.filtered('partner_id'):
    #         # el compute_withholdings o el _compute_withholdings?
    #         rec._compute_withholdings()
    #         # rec.force_amount_company_currency += rec.payment_difference
    #         # rec.unreconciled_amount = rec.to_pay_amount - rec.selected_debt

    def action_confirm(self):
        checks_payments = self.filtered(
            lambda x: x.payment_method_code in ["in_third_party_checks", "out_third_party_checks"]
        )
        for rec in checks_payments:
            previous_to_pay = rec.to_pay_amount
            rec.compute_withholdings()
            if not rec.currency_id.is_zero(previous_to_pay - rec.to_pay_amount):
                raise UserError(
                    "Está pagando con un cheque y las retenciones que se aplicarán cambiarán el importe a pagar de %s a %s.\n"
                    "Por favor, compute las retenciones para que el importe a pagar se actualice y luego confirme el pago."
                    % (previous_to_pay, rec.to_pay_amount)
                )
        self.compute_withholdings()
        res = super().action_confirm()
        # por ahora primero computamos retenciones y luego conifmamos porque si no en caso de cheques siempre da error
        # TODO tal vez mejorar y advertir de que se va a computar el importe?
        return res

    def _prepare_move_withholding_lines(self, default_values):
        res = super()._prepare_move_withholding_lines(default_values)
        if self.is_internal_transfer:
            return res

        self.ensure_one()
        sign = 1
        if self.payment_type == "outbound":
            sign = -1

        conversion_rate = self.exchange_rate or 1.0
        # Cuando el pago es en moneda extranjera, las retenciones se calculan en moneda de la compañía (ARS).
        # Usamos moneda de la compañía en las move lines de retención para evitar que _inverse_amount_currency
        # recalcule el balance a partir de un amount_currency redondeado en moneda extranjera, lo que produce
        # diferencias de redondeo (ej: 84,894.75 ARS -> 60 USD -> 84,900 ARS en el roundtrip).
        use_company_currency = self.currency_id != self.company_id.currency_id

        # Omitimos apuntes contables para líneas que no sean de ganancias y tengan importe cero;
        # el resto (ganancias, o no-ganancias con importe > 0) sí genera apunte.
        lines_with_accounting_entry = self.l10n_ar_withholding_line_ids.filtered(
            lambda l: l.tax_id.l10n_ar_tax_type in ["earnings", "earnings_scale"] or l.amount
        )

        for line in lines_with_accounting_entry:
            # nuestro approach esta quedando distinto al del wizard. En nuestras lineas tenemos los importes en moneda
            # de la cia, por lo cual el line.amount aca representa eso y tenemos que convertirlo para el amount_currency

            __, account_id, tax_repartition_line_id, __ = line._tax_compute_all_helper()
            balance = self.company_id.currency_id.round(sign * line.amount)
            if use_company_currency:
                amount_currency = balance
                currency_id = self.company_id.currency_id.id
            else:
                amount_currency = self.currency_id.round(balance / conversion_rate)
                currency_id = self.currency_id.id
            res.append(
                {
                    **self._get_withholding_move_line_default_values(),
                    "name": line.name,
                    "account_id": account_id,
                    "balance": balance,
                    "amount_currency": amount_currency,
                    "currency_id": currency_id,
                    "tax_base_amount": sign * line.base_amount,
                    "tax_repartition_line_id": tax_repartition_line_id,
                }
            )

        for base_amount in list(set(lines_with_accounting_entry.mapped("base_amount"))):
            withholding_lines = lines_with_accounting_entry.filtered(lambda x: x.base_amount == base_amount)
            nice_base_label = ",".join(withholding_lines.filtered("name").mapped("name"))
            account_id = self.company_id.l10n_ar_tax_base_account_id.id
            balance = self.company_id.currency_id.round(sign * base_amount)
            if use_company_currency:
                amount_currency = balance
                currency_id = self.company_id.currency_id.id
            else:
                # informamos el amount_currency para que Odoo no resetee el balance a 0.0 por inconsistencia de moneda
                amount_currency = self.currency_id.round(balance / conversion_rate)
                currency_id = self.currency_id.id
            res.append(
                {
                    **self._get_withholding_move_line_default_values(),
                    "name": _("Base Ret: ") + nice_base_label,
                    "tax_ids": [Command.set(withholding_lines.mapped("tax_id").ids)],
                    "account_id": account_id,
                    "balance": balance,
                    "amount_currency": amount_currency,
                    "currency_id": currency_id,
                }
            )
            res.append(
                {
                    **self._get_withholding_move_line_default_values(),  # Counterpart 0 operation
                    "name": _("Base Ret Cont: ") + nice_base_label,
                    "account_id": account_id,
                    "balance": -balance,
                    "amount_currency": -amount_currency,
                    "currency_id": currency_id,
                }
            )

        return res

    def _prepare_move_lines_per_type(self, write_off_line_vals=None, force_balance=None):
        res = super()._prepare_move_lines_per_type(write_off_line_vals=write_off_line_vals, force_balance=force_balance)

        # we adjust liquidity and counterpart lines because in ARG payment amount is already net of withholdings
        # whereas odoo expects it to be gross and subtracts withholdings from it.
        wth_lines = res.get("withholding_lines", [])

        if wth_lines:
            wth_balance = sum(line["balance"] for line in wth_lines)
            # Suma directa de amount_currency de las líneas de retención. Cuando el pago es en moneda
            # extranjera, las withholding lines usan moneda de compañía (ARS) y por lo tanto este valor
            # está en ARS. Lo usamos para revertir el ajuste que hizo base Odoo sobre la liquidez.
            raw_wth_amount_currency = sum(line["amount_currency"] for line in wth_lines)

            # Para ajustar la contrapartida necesitamos el equivalente en moneda del pago.
            # Cuando el pago es en moneda extranjera, lo convertimos; si no, es el mismo valor.
            if self.currency_id != self.company_id.currency_id:
                conversion_rate = self.exchange_rate or 1.0
                wth_amount_currency_pay = self.currency_id.round(wth_balance / conversion_rate)
            else:
                wth_amount_currency_pay = raw_wth_amount_currency

            # Cuando force_amount_company_currency está activo, account_payment_pro ya estableció el balance
            # correcto en la línea de liquidez (monto neto de retenciones) y ajustó la contrapartida para que
            # el asiento cuadre. Si aquí volvemos a sumar/restar wth_balance sobre los balances, se produce un
            # doble ajuste que rompe los importes en moneda de compañía. Por eso, solo ajustamos los balances
            # cuando NO hay monto forzado.
            has_forced_amount = bool(self.force_amount_company_currency)

            liquidity_lines = res.get("liquidity_lines", [])
            if liquidity_lines:
                if not has_forced_amount:
                    liquidity_lines[0]["balance"] += wth_balance
                # Revertimos el ajuste de amount_currency que hizo base Odoo (usó raw_wth_amount_currency
                # para restarlo de la liquidez).
                liquidity_lines[0]["amount_currency"] += raw_wth_amount_currency
                # if after adjustment the liquidity line is 0, we remove it
                # esto podria ir a payment_pro y que cualquier liquidity line en zero no se cree (Es para caso de
                # puro write off y/o solo retenciones)
                if self.company_currency_id.is_zero(liquidity_lines[0]["balance"]):
                    res["liquidity_lines"] = []
            counterpart_lines = res.get("counterpart_lines", [])
            if counterpart_lines:
                # the counterpart line (debt) should be the gross amount (net + withholdings)
                if not has_forced_amount:
                    counterpart_lines[0]["balance"] -= wth_balance
                    sign = 1 if counterpart_lines[0]["balance"] >= 0 else -1
                    counterpart_lines[0]["amount_currency"] = sign * abs(counterpart_lines[0]["amount_currency"])
                # Solo sumo el valor de la retencion si no uso moneda de contrpartida
                # porque sino ya esta incluido el total en el campo amount_currency
                # Porque lo cambio Payment pro
                if not self._use_counterpart_currency():
                    # Usamos el equivalente en moneda del pago (no la suma raw) para que el
                    # amount_currency de la contrapartida quede correctamente en la moneda del pago.
                    counterpart_lines[0]["amount_currency"] -= wth_amount_currency_pay

        return res

    def action_post(self):
        for rec in self:
            commands = []
            for line in rec.l10n_ar_withholding_line_ids:
                if not line.name or line.name == "/":
                    if line.tax_id.l10n_ar_withholding_sequence_id:
                        commands.append(
                            Command.update(
                                line.id,
                                {
                                    "name": line.tax_id.l10n_ar_withholding_sequence_id.next_by_id()
                                    if line.amount
                                    else "/"
                                },
                            )
                        )
                    else:
                        raise UserError(
                            _("Please enter withholding number for tax %s or configure a sequence on that tax")
                            % line.tax_id.name
                        )
                if commands:
                    rec.l10n_ar_withholding_line_ids = commands

        return super().action_post()

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ("l10n_ar_withholding_line_ids",)

    @api.depends(
        "currency_id", "company_id", "l10n_ar_withholding_line_ids", "destination_account_id", "counterpart_currency_id"
    )
    def _compute_withholding_warning(self):
        """Para todos los pagos con retenciones verificamos que la deuda se esté conciliando en moneda local
        ya que todavía no tenemos implementado cálculos de retenciones ajustados por diferencia de cambio"""
        self.withholding_warning = False
        for rec in self.filtered(
            lambda x: x.state == "draft"
            and x.l10n_ar_withholding_line_ids
            and (x.currency_id != x.company_id.currency_id or x._use_counterpart_currency())
        ):
            # Verificar si la deuda está gestionada en moneda extranjera
            dest_currency = rec.destination_account_id.currency_id
            debt_in_foreign_currency = dest_currency and dest_currency != rec.company_id.currency_id
            if not rec.company_id.reconcile_on_company_currency or debt_in_foreign_currency:
                rec.withholding_warning = True

    ###################################################
    # desde account_withholding_automatic payment.group
    ###################################################

    # withholdings_amount = fields.Monetary(
    #     compute='_compute_withholdings_amount'
    # )
    withholdable_advanced_amount = fields.Monetary(
        "Adjustment / Advance (untaxed)",
        help="Used for withholdings calculation",
        currency_field="company_currency_id",
        compute="_compute_withholdable_advanced_amount",
        copy=False,
        store=True,
        readonly=False,
    )
    selected_debt_untaxed = fields.Monetary(
        # string='To Pay lines Amount',
        compute="_compute_selected_debt_untaxed",
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
            sign = rec.partner_type == "supplier" and -1.0 or 1.0
            for line in rec.matched_move_line_ids.with_context(matched_payment_ids=rec.ids):
                invoice = line.move_id
                factor = invoice and invoice._get_tax_factor() or 1.0
                # TODO implementar
                matched_amount_untaxed += line.payment_matched_amount * factor
            rec.matched_amount_untaxed = sign * matched_amount_untaxed

    @api.depends("to_pay_move_line_ids")
    def _compute_selected_debt_untaxed(self):
        for rec in self:
            selected_debt_untaxed = 0.0
            for line in rec.to_pay_move_line_ids._origin:
                # factor for total_untaxed
                invoice = line.move_id
                factor = invoice and invoice._get_tax_factor() or 1.0
                selected_debt_untaxed += line.amount_residual * factor
            rec.selected_debt_untaxed = selected_debt_untaxed * (rec.partner_type == "supplier" and -1.0 or 1.0)

    @api.depends("unreconciled_amount")
    def _compute_withholdable_advanced_amount(self):
        for rec in self:
            rec.withholdable_advanced_amount = rec.unreconciled_amount

    @api.depends("l10n_ar_fiscal_position_id", "partner_id", "company_id", "date")
    def _compute_l10n_ar_withholding_line_ids(self):
        # metodo completamente analogo a payment.register._compute_l10n_ar_withholding_ids
        for rec in self.filtered(lambda x: x.partner_type == "supplier"):
            date = rec.date or fields.Date.today()
            withholdings = [Command.clear()]
            if rec.l10n_ar_fiscal_position_id.l10n_ar_tax_ids:
                taxes = rec.l10n_ar_fiscal_position_id._l10n_ar_add_taxes(
                    rec.partner_id, rec.company_id, date, "withholding", rec
                )
                withholdings += [Command.create({"tax_id": x.id}) for x in taxes]
            rec.l10n_ar_withholding_line_ids = withholdings

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
                        "Máximo de intentos alcanzado. No pudimos computar el importe a pagar. El último importe a pagar"
                        'al que llegamos fue "%s"' % rec.to_pay_amount
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
            rec.with_context(skip_account_move_synchronization=False)._synchronize_to_moves(
                {"l10n_ar_withholding_line_ids"}
            )

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
            return f"{self.company_id.id}-{self.partner_id.id}-{self.payment_type}-{self.currency_id.id if self.other_currency else self.counterpart_currency_id.id}"
        return self.id

    def _get_payment_bundles(self):
        """Returns a dictionary of payment bundles, where the key is a tuple
        of (company_id, partner_id, payment_type, currency_id) and the value
        is a recordset of account.payment."""
        bundles = defaultdict(lambda: self.env["account.payment"])
        for rec in self:
            bundles[rec._get_payment_bundle_key()] += rec
        return bundles

    def _select_bundle(self, bundles):
        """Selects a bundle from the dictionary of payment bundles based on
        the current record's company_id, partner_id, payment_type, and
        currency_id."""
        self.ensure_one()
        return bundles.get(self._get_payment_bundle_key())
