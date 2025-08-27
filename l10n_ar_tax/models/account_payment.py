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

    @api.depends("to_pay_move_line_ids", "partner_id")
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

    @api.depends("l10n_ar_withholding_line_ids.amount")
    def _compute_withholdings_amount(self):
        for rec in self:
            rec.withholdings_amount = sum(rec.l10n_ar_withholding_line_ids.mapped("amount"))

    def _get_withholding_move_line_default_values(self):
        return {
            "currency_id": self.currency_id.id,
        }

    @api.depends("l10n_ar_withholding_line_ids.amount")
    def _compute_payment_total(self):
        super()._compute_payment_total()
        for rec in self:
            rec.payment_total += sum(rec.l10n_ar_withholding_line_ids.mapped("amount"))

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
        for rec in self.filtered(lambda x: x.partner_type == "supplier" and not x._is_latam_check_payment()):
            # el compute_withholdings o el _compute_withholdings?
            amount = rec.amount + rec.payment_difference
            # no pasamos a importes negativos (por ej. si se ponene retenciones grandes) porque es molesto
            # empieza a salir un raise que no deja editar cosas
            rec.amount = amount if amount > 0 else 0
            # rec.unreconciled_amount = rec.to_pay_amount - rec.selected_debt

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

    def _prepare_witholding_write_off_vals(self):
        self.ensure_one()
        write_off_line_vals = []
        conversion_rate = self.exchange_rate or 1.0
        sign = 1
        if self.payment_type == "outbound":
            sign = -1
        for line in self.l10n_ar_withholding_line_ids:
            # nuestro approach esta quedando distinto al del wizard. En nuestras lineas tenemos los importes en moneda
            # de la cia, por lo cual el line.amount aca representa eso y tenemos que convertirlo para el amount_currency

            __, account_id, tax_repartition_line_id, __ = line._tax_compute_all_helper()
            amount_currency = self.currency_id.round(line.amount / conversion_rate)
            write_off_line_vals.append(
                {
                    **self._get_withholding_move_line_default_values(),
                    "name": line.name,
                    "account_id": account_id,
                    "amount_currency": sign * amount_currency,
                    "balance": sign * line.amount,
                    "tax_base_amount": sign * line.base_amount,
                    "tax_repartition_line_id": tax_repartition_line_id,
                }
            )

        for base_amount in list(set(self.l10n_ar_withholding_line_ids.mapped("base_amount"))):
            withholding_lines = self.l10n_ar_withholding_line_ids.filtered(lambda x: x.base_amount == base_amount)
            nice_base_label = ",".join(withholding_lines.filtered("name").mapped("name"))
            account_id = self.company_id.l10n_ar_tax_base_account_id.id
            base_amount = sign * base_amount
            base_amount_currency = self.currency_id.round(base_amount / conversion_rate)
            write_off_line_vals.append(
                {
                    **self._get_withholding_move_line_default_values(),
                    "name": _("Base Ret: ") + nice_base_label,
                    "tax_ids": [Command.set(withholding_lines.mapped("tax_id").ids)],
                    "account_id": account_id,
                    "balance": base_amount,
                    "amount_currency": base_amount_currency,
                }
            )
            write_off_line_vals.append(
                {
                    **self._get_withholding_move_line_default_values(),  # Counterpart 0 operation
                    "name": _("Base Ret Cont: ") + nice_base_label,
                    "account_id": account_id,
                    "balance": -base_amount,
                    "amount_currency": -base_amount_currency,
                }
            )

        return write_off_line_vals

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

    @api.constrains("currency_id", "company_id", "l10n_ar_withholding_line_ids")
    def _check_withholdings_and_currency(self):
        for rec in self:
            if rec.l10n_ar_withholding_line_ids and rec.currency_id != rec.company_id.currency_id:
                raise UserError(_('Withholdings must be done in "%s" currency') % rec.company_id.currency_id.name)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        res = super()._prepare_move_line_default_vals(write_off_line_vals, force_balance=force_balance)
        res += self._prepare_witholding_write_off_vals()
        wth_amount = sum(self.l10n_ar_withholding_line_ids.mapped("amount"))
        conversion_rate = self.exchange_rate or 1.0
        # TODO: EVALUAR
        # si cambio el valor de la cuenta de liquides quitando las retenciones el campo amount representa el monto que cancelo de la deuda
        # si cambio la cuenta de contraparte (agregando retenciones) el campo amount representa el monto neto que abono al partner
        # Ambos caminos funcionan pero no se cual es mejor a nivel usabilidad. depende como realizemos el calculo automatico de la ret
        # liquidity_accounts = [x.id for x in self._get_valid_liquidity_accounts() if x]
        valid_account_types = self._get_valid_payment_account_types()
        for line in res:
            account_id = self.env["account.account"].browse(line["account_id"])
            # if line['account_id'] in liquidity_accounts:
            if account_id.account_type in valid_account_types:
                if self.payment_type == "inbound" and "credit" in line:
                    line["credit"] += wth_amount
                    if not self._use_counterpart_currency():
                        line["amount_currency"] -= wth_amount / conversion_rate
                elif self.payment_type == "outbound" and "debit" in line:
                    line["debit"] += wth_amount
                    if not self._use_counterpart_currency():
                        line["amount_currency"] += wth_amount / conversion_rate
        return res

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
                    rec.partner_id, rec.company_id, date, "withholding"
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
