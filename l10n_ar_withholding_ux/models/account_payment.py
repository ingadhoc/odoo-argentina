from ast import literal_eval

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    l10n_ar_withholding_line_ids = fields.One2many(
        'l10n_ar.payment.withholding', 'payment_id', string='Withholdings Lines',
        # compute='_compute_l10n_ar_withholding_line_ids', readonly=False, store=True
    )
    withholdings_amount = fields.Monetary(
        compute='_compute_withholdings_amount',
        currency_field='company_currency_id',
    )

    @api.depends('l10n_ar_withholding_line_ids.amount')
    def _compute_withholdings_amount(self):
        for rec in self:
            rec.withholdings_amount = sum(rec.l10n_ar_withholding_line_ids.mapped('amount'))

    def _get_withholding_move_line_default_values(self):
        return {
            'currency_id': self.currency_id.id,
        }

    @api.depends('l10n_ar_withholding_line_ids.amount')
    def _compute_payment_total(self):
        super()._compute_payment_total()
        for rec in self:
            rec.payment_total += sum(rec.l10n_ar_withholding_line_ids.mapped('amount'))

    @api.onchange('withholdings_amount')
    def _onchange_withholdings(self):
        for rec in self.filtered(lambda x: x.payment_method_code not in ['in_third_party_checks', 'out_third_party_checks']):
            # el compute_withholdings o el _compute_withholdings?
            rec.amount += rec.payment_difference
            # rec.unreconciled_amount = rec.to_pay_amount - rec.selected_debt

    # ver mensaje en commit
    # @api.onchange('to_pay_amount', 'withholdable_advanced_amount', 'partner_id')
    # def _onchange_to_pay_amount(self):
    #     # para muchas retenciones es necesario que el partner este seteado, solo calculamos si viene definido
    #     for rec in self.filtered('partner_id'):
    #         # el compute_withholdings o el _compute_withholdings?
    #         rec._compute_withholdings()
    #         rec.force_amount_company_currency += rec.payment_difference
    #         # rec.unreconciled_amount = rec.to_pay_amount - rec.selected_debt

    # Por ahora no compuamos para no pisar cosas que pueda haber moficiado el usuario. Ademas que ya era así (manual)
    # en version anterior
    # @api.depends('state', 'move_id')
    # def _compute_l10n_ar_withholding_line_ids(self):
    #     for rec in self:
    #         l10n_ar_withholding_line_ids = [Command.clear()]
    #         for line in rec.move_id.line_ids.filtered(lambda x: x.tax_line_id):
    #             base = sum(rec.line_ids.filtered(lambda x: line.tax_line_id.id in x.tax_ids.ids).mapped('balance'))
    #             l10n_ar_withholding_line_ids += [Command.create({'name': line.name, 'tax_id': line.tax_line_id.id,
    #                                                             'base_amount': abs(base), 'amount': abs(line.balance)})]
    #         rec.l10n_ar_withholding_line_ids = l10n_ar_withholding_line_ids

    def action_confirm(self):
        checks_payments = self.filtered(lambda x: x.payment_method_code in ['in_third_party_checks', 'out_third_party_checks'])
        for rec in checks_payments:
            previous_to_pay = rec.to_pay_amount
            rec.compute_withholdings()
            if not rec.currency_id.is_zero(previous_to_pay - rec.to_pay_amount):
                raise UserError(
                    'Está pagando con un cheque y las retenciones que se aplicarán cambiarán el importe a pagar de %s a %s.\n'
                    'Por favor, compute las retenciones para que el importe a pagar se actualice y luego confirme el pago.' % (
                        previous_to_pay, rec.to_pay_amount
                    ))
        self.filtered('company_id.automatic_withholdings').compute_withholdings()
        res = super().action_confirm()
        # por ahora primero computamos retenciones y luego conifmamos porque si no en caso de cheques siempre da error
        # TODO tal vez mejorar y advertir de que se va a computar el importe?
        return res

    def _prepare_witholding_write_off_vals(self):
        self.ensure_one()
        write_off_line_vals = []
        conversion_rate = self.exchange_rate or 1.0
        sign = 1
        if self.partner_type == 'supplier':
            sign = -1
        for line in self.l10n_ar_withholding_line_ids:
            # nuestro approach esta quedando distinto al del wizard. En nuestras lineas tenemos los importes en moneda
            # de la cia, por lo cual el line.amount aca representa eso y tenemos que convertirlo para el amount_currency
            account_id, tax_repartition_line_id = line._tax_compute_all_helper()
            amount_currency = self.currency_id.round(line.amount / conversion_rate)
            write_off_line_vals.append({
                    **self._get_withholding_move_line_default_values(),
                    'name': line.name,
                    'account_id': account_id,
                    'amount_currency': sign * amount_currency,
                    'balance': sign * line.amount,
                    # este campo no existe mas
                    # 'tax_base_amount': sign * line.base_amount,
                    'tax_repartition_line_id': tax_repartition_line_id,
            })

        for base_amount in list(set(self.l10n_ar_withholding_line_ids.mapped('base_amount'))):
            withholding_lines = self.l10n_ar_withholding_line_ids.filtered(lambda x: x.base_amount == base_amount)
            nice_base_label = ','.join(withholding_lines.filtered('name').mapped('name'))
            account_id = self.company_id.l10n_ar_tax_base_account_id.id
            base_amount = sign * base_amount
            base_amount_currency = self.currency_id.round(base_amount / conversion_rate)
            write_off_line_vals.append({
                **self._get_withholding_move_line_default_values(),
                'name': _('Base Ret: ') + nice_base_label,
                'tax_ids': [Command.set(withholding_lines.mapped('tax_id').ids)],
                'account_id': account_id,
                'balance': base_amount,
                'amount_currency': base_amount_currency,
            })
            write_off_line_vals.append({
                **self._get_withholding_move_line_default_values(),  # Counterpart 0 operation
                'name': _('Base Ret Cont: ') + nice_base_label,
                'account_id': account_id,
                'balance': -base_amount,
                'amount_currency': -base_amount_currency,
            })

        return write_off_line_vals

    def action_post(self):
        for rec in self:
            commands = []
            for line in rec.l10n_ar_withholding_line_ids:
                if (not line.name or line.name == '/'):
                    if line.tax_id.l10n_ar_withholding_sequence_id:
                        commands.append(Command.update(line.id, {'name': line.tax_id.l10n_ar_withholding_sequence_id.next_by_id()}))
                    else:
                        raise UserError(_('Please enter withholding number for tax %s or configure a sequence on that tax') % line.tax_id.name)
                if commands:
                    rec.l10n_ar_withholding_line_ids = commands

        return super().action_post()

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ('l10n_ar_withholding_line_ids',)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        res = super()._prepare_move_line_default_vals(write_off_line_vals, force_balance=force_balance)
        res += self._prepare_witholding_write_off_vals()
        wth_amount = sum(self.l10n_ar_withholding_line_ids.mapped('amount'))
        # TODO: EVALUAR
        # si cambio el valor de la cuenta de liquides quitando las retenciones el campo amount representa el monto que cancelo de la deuda
        # si cambio la cuenta de contraparte (agregando retenciones) el campo amount representa el monto neto que abono al partner
        # Ambos caminos funcionan pero no se cual es mejor a nivel usabilidad. depende como realizemos el calculo automatico de la ret
        # liquidity_accounts = [x.id for x in self._get_valid_liquidity_accounts() if x]
        valid_account_types = self._get_valid_payment_account_types()

        for line in res:
            account_id = self.env['account.account'].browse(line['account_id'])
            # if line['account_id'] in liquidity_accounts:
            if account_id.account_type in valid_account_types:
                if self.payment_type == 'inbound':
                    line['credit'] += wth_amount
                    line['amount_currency'] -= wth_amount
                elif self.payment_type == 'outbound':
                    line['debit'] += wth_amount
                    line['amount_currency'] += wth_amount
        return res

    ###################################################
    # desde account_withholding_automatic payment.group
    ###################################################

    # withholdings_amount = fields.Monetary(
    #     compute='_compute_withholdings_amount'
    # )
    withholdable_advanced_amount = fields.Monetary(
        'Adjustment / Advance (untaxed)',
        help='Used for withholdings calculation',
        currency_field='company_currency_id',
    )
    selected_debt_untaxed = fields.Monetary(
        # string='To Pay lines Amount',
        string='Selected Debt Untaxed',
        compute='_compute_selected_debt_untaxed',
    )
    matched_amount_untaxed = fields.Monetary(
        compute='_compute_matched_amount_untaxed',
        currency_field='currency_id',
    )

    def _compute_matched_amount_untaxed(self):
        """ Lo separamos en otro metodo ya que es un poco mas costoso y no se
        usa en conjunto con matched_amount
        """
        for rec in self:
            rec.matched_amount_untaxed = 0.0
            if rec.state != 'posted':
                continue
            matched_amount_untaxed = 0.0
            sign = rec.partner_type == 'supplier' and -1.0 or 1.0
            for line in rec.matched_move_line_ids.with_context(matched_payment_ids=rec.ids):
                invoice = line.move_id
                factor = invoice and invoice._get_tax_factor() or 1.0
                # TODO implementar
                matched_amount_untaxed += line.payment_matched_amount * factor
            rec.matched_amount_untaxed = sign * matched_amount_untaxed

    @api.depends(
        'to_pay_move_line_ids.amount_residual',
        'to_pay_move_line_ids.amount_residual_currency',
        'to_pay_move_line_ids.currency_id',
        'to_pay_move_line_ids.move_id',
        'date',
        'currency_id',
    )
    def _compute_selected_debt_untaxed(self):
        for rec in self:
            selected_debt_untaxed = 0.0
            for line in rec.to_pay_move_line_ids._origin:
                # factor for total_untaxed
                invoice = line.move_id
                factor = invoice and invoice._get_tax_factor() or 1.0
                selected_debt_untaxed += line.amount_residual * factor
            rec.selected_debt_untaxed = selected_debt_untaxed * (rec.partner_type == 'supplier' and -1.0 or 1.0)

    @api.onchange('unreconciled_amount')
    def set_withholdable_advanced_amount(self):
        for rec in self:
            rec.withholdable_advanced_amount = rec.unreconciled_amount

    def _compute_withholdings(self):
        # chequeamos lineas a pagar antes de computar impuestos para evitar trabajar sobre base erronea
        self._check_to_pay_lines_account()
        for rec in self:
            if rec.partner_type != 'supplier':
                continue
            # limpiamos el type por si se paga desde factura ya que el en ese
            # caso viene in_invoice o out_invoice y en search de tax filtrar
            # por impuestos de venta y compra (y no los nuestros de pagos
            # y cobros)
            taxes = self.env['account.tax'].with_context(type=None).search([
                    ('type_tax_use', '=', 'none'),
                    # TODo corroborar en 16
                    ('withholding_type', '!=', 'none'),
                    ('l10n_ar_withholding_payment_type', '=', rec.partner_type),
                    ('company_id', '=', rec.company_id.id),
                ])

            rec._upadte_withholdings(taxes)

    def compute_withholdings(self):
        self._compute_withholdings()
        self._onchange_withholdings()

    def compute_to_pay_amount_for_check(self):
        checks_payments = self.filtered(lambda x: x.payment_method_code in ['in_third_party_checks', 'out_third_party_checks'])
        for rec in checks_payments.with_context(skip_account_move_synchronization=True):
            rec.set_withholdable_advanced_amount()
            rec._compute_withholdings()
            # dejamos 230 porque el hecho de estar usando valor de "$2" abajo y subir de a un centavo hace podamos necesitar
            # 200 intento solo en esa seccion
            # deberiamos ver de ir aproximando de otra manera
            remining_attemps = 230
            while not rec.currency_id.is_zero(rec.payment_difference):
                if remining_attemps == 0:
                    raise UserError(
                        'Máximo de intentos alcanzado. No pudimos computar el importe a pagar. El último importe a pagar'
                        'al que llegamos fue "%s"' % rec.to_pay_amount)
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
                        'Hubo un error al querer computar el importe a pagar. Llegamos a estos valores:\n'
                        '* to_pay_amount: %s\n'
                        '* payment_difference: %s\n'
                        '* amount: %s'
                        % (rec.to_pay_amount, rec.payment_difference, rec.amount))
                rec.set_withholdable_advanced_amount()
                rec._compute_withholdings()
            rec.with_context(skip_account_move_synchronization=False)._synchronize_to_moves({'l10n_ar_withholding_line_ids'})

    def _upadte_withholdings(self, taxes):
        self.ensure_one()
        commands = []
        for tax in taxes:
            if (
                    tax.withholding_user_error_message and
                    tax.withholding_user_error_domain):
                try:
                    domain = literal_eval(tax.withholding_user_error_domain)
                except Exception as e:
                    raise ValidationError(_(
                        'Could not eval rule domain "%s".\n'
                        'This is what we get:\n%s' % (tax.withholding_user_error_domain, e)))
                domain.append(('id', '=', self.id))
                if self.search(domain):
                    raise ValidationError(tax.withholding_user_error_message)
            vals = tax.get_withholding_vals(self)

            # we set computed_withholding_amount, hacemos round porque
            # si no puede pasarse un valor con mas decimales del que se ve
            # y terminar dando error en el asiento por debitos y creditos no
            # son iguales, algo parecido hace odoo en el compute_all de taxes
            currency = self.currency_id
            period_withholding_amount = currency.round(vals.get('period_withholding_amount', 0.0))
            previous_withholding_amount = currency.round(vals.get('previous_withholding_amount'))
            # withholding can not be negative
            computed_withholding_amount = max(0, (period_withholding_amount - previous_withholding_amount))

            payment_withholding = self.l10n_ar_withholding_line_ids.filtered(lambda x: x.tax_id == tax)
            if not computed_withholding_amount:
                # if on refresh no more withholding, we delete if it exists
                if payment_withholding:
                    commands.append(Command.delete(payment_withholding.id))
                continue

            # we copy withholdable_base_amount on base_amount
            # al final vimos con varios clientes que este monto base
            # debe ser la base imponible de lo que se está pagando en este
            # voucher
            vals['base_amount'] = vals.get('withholdable_advanced_amount') + vals.get('withholdable_invoiced_amount')
            vals['amount'] = computed_withholding_amount
            vals['computed_withholding_amount'] = computed_withholding_amount

            # por ahora no imprimimos el comment, podemos ver de llevarlo a
            # otro campo si es de utilidad
            vals.pop('comment')
            if payment_withholding:
                commands.append(Command.update(payment_withholding.id, vals))
                # payment_withholding.write(vals)
            else:
                # TODO implementar devoluciones de retenciones
                # TODO en vez de pasarlo asi usar un command create
                vals['payment_id'] = self.id
                commands.append(Command.create(vals))
        self.l10n_ar_withholding_line_ids = commands

    def _get_withholdable_amounts(
            self, withholding_amount_type, withholding_advances):
        """ Method to help on getting withholding amounts from account.tax
        """
        self.ensure_one()
        # Por compatibilidad con public_budget aceptamos
        # pagos en otros estados no validados donde el matched y
        # unmatched no se computaron, por eso agragamos la condición
        if self.state == 'posted':
            untaxed_field = 'matched_amount_untaxed'
            total_field = 'matched_amount'
        else:
            untaxed_field = 'selected_debt_untaxed'
            total_field = 'selected_debt'

        if withholding_amount_type == 'untaxed_amount':
            withholdable_invoiced_amount = self[untaxed_field]
        else:
            withholdable_invoiced_amount = self[total_field]

        withholdable_advanced_amount = 0.0
        # if the unreconciled_amount is negative, then the user wants to make
        # a partial payment. To get the right untaxed amount we need to know
        # which invoice is going to be paid, we only allow partial payment
        # on last invoice.
        # If the payment is posted the withholdable_invoiced_amount is
        # the matched amount
        if self.withholdable_advanced_amount < 0.0 and \
                self.to_pay_move_line_ids and self.state != 'posted':
            withholdable_advanced_amount = 0.0

            sign = self.partner_type == 'supplier' and -1.0 or 1.0
            sorted_to_pay_lines = sorted(
                self.to_pay_move_line_ids,
                key=lambda a: a.date_maturity or a.date)

            # last line to be reconciled
            partial_line = sorted_to_pay_lines[-1]
            if sign * partial_line.amount_residual < \
                    sign * self.withholdable_advanced_amount:
                raise ValidationError(_(
                    'Seleccionó deuda por %s pero aparentente desea pagar '
                    ' %s. En la deuda seleccionada hay algunos comprobantes de'
                    ' mas que no van a poder ser pagados (%s). Deberá quitar '
                    ' dichos comprobantes de la deuda seleccionada para poder '
                    'hacer el correcto cálculo de las retenciones.' % (
                        self.selected_debt,
                        self.to_pay_amount,
                        partial_line.move_id.display_name,
                        )))

            if withholding_amount_type == 'untaxed_amount' and \
                    partial_line.move_id:
                invoice_factor = partial_line.move_id._get_tax_factor()
            else:
                invoice_factor = 1.0

            # si el adelanto es negativo estamos pagando parcialmente una
            # factura y ocultamos el campo sin impuesto ya que lo sacamos por
            # el proporcional descontando de el iva a lo que se esta pagando
            withholdable_invoiced_amount -= (
                sign * self.unreconciled_amount * invoice_factor)
        elif withholding_advances:
            # si el pago esta publicado obtenemos los valores de los importes
            # conciliados (porque el pago pudo prepararse como adelanto
            # pero luego haberse conciliado y en ese caso lo estariamos sumando
            # dos veces si lo usamos como base de otros pagos). Si estan los
            # campos withholdable_advanced_amount y unreconciled_amount le
            # sacamos el proporcional correspondiente
            if self.state == 'posted':
                if self.unreconciled_amount and \
                   self.withholdable_advanced_amount:
                    withholdable_advanced_amount = self.amount_residual * (
                        self.withholdable_advanced_amount /
                        self.unreconciled_amount)
                else:
                    withholdable_advanced_amount = self.amount_residual
            else:
                withholdable_advanced_amount = \
                    self.withholdable_advanced_amount
        return (withholdable_advanced_amount, withholdable_invoiced_amount)

    def _get_name_receipt_report(self, report_xml_id):
        """ Method similar to the '_get_name_invoice_report' of l10n_latam_invoice_document
        Basically it allows different localizations to define it's own report
        This method should actually go in a sale_ux module that later can be extended by different localizations
        Another option would be to use report_substitute module and setup a subsitution with a domain
        """
        self.ensure_one()
        if self.company_id.country_id.code == 'AR':
            return 'l10n_ar_withholding_ux.report_payment_receipt_document'
        return report_xml_id
