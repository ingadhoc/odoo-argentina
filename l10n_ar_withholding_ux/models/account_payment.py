from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError
from ast import literal_eval


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    # l10n_ar_withholding_line_ids = fields.One2many(
    #     'l10n_ar.payment.withholding', 'payment_id', string='Withholdings Lines',
    #     compute='_compute_l10n_ar_withholding_line_ids', readonly=False, store=True
    # )
    l10n_ar_amount_total = fields.Monetary('Amount Total', compute='_compute_l10n_ar_amount_total', readonly=True,
                                           help="Total amount after withholdings", currency_field='company_currency_id')

    def _get_withholding_move_line_default_values(self):
        return {
            'currency_id': self.currency_id.id,
        }

    @api.depends('l10n_ar_withholding_ids.balance', 'amount', 'state')
    def _compute_l10n_ar_amount_total(self):
        for rec in self:
            rec.l10n_ar_amount_total = rec.amount_company_currency_signed_pro + sum(rec.l10n_ar_withholding_ids.mapped('balance'))
            # rec.l10n_ar_amount_total = rec.amount + sum(rec.l10n_ar_withholding_line_ids.mapped('amount'))

    # @api.depends('state', 'move_id')
    # def _compute_l10n_ar_withholding_line_ids(self):
    #     for rec in self:
    #         l10n_ar_withholding_line_ids = [Command.clear()]
    #         for line in rec.move_id.line_ids.filtered(lambda x: x.tax_line_id):
    #             base = sum(rec.line_ids.filtered(lambda x: line.tax_line_id.id in x.tax_ids.ids).mapped('balance'))
    #             l10n_ar_withholding_line_ids += [Command.create({'name': line.name, 'tax_id': line.tax_line_id.id,
    #                                                             'base_amount': abs(base), 'amount': abs(line.balance)})]
    #         rec.l10n_ar_withholding_line_ids = l10n_ar_withholding_line_ids

    def _prepare_witholding_write_off_vals(self):
        self.ensure_one()
        write_off_line_vals = []
        conversion_rate = self.exchange_rate or 1.0
        sign = 1
        if self.partner_type == 'supplier':
            sign = -1
        for line in self.l10n_ar_withholding_ids:
            # nuestro approach esta quedando distinto al del wizard. En nuestras lineas tenemos los importes en moneda
            # de la cia, por lo cual el line.amount aca representa eso y tenemos que convertirlo para el amount_currency
            account_id, tax_repartition_line_id = line._tax_compute_all_helper()
            if isinstance(line.id, models.NewId):
                amount_currency = self.currency_id.round(line.balance / conversion_rate)
                write_off_line_vals.append({
                        **self._get_withholding_move_line_default_values(),
                        'name': line.name,
                        'account_id': account_id,
                        'amount_currency': amount_currency,
                        'balance': line.balance,
                        # este campo no existe mas
                        # 'tax_base_amount': sign * line.base_amount,
                        'tax_repartition_line_id': tax_repartition_line_id,
                })
            # else:
            #     line.account_id = account_id
            #     line.tax_repartition_line_id = tax_repartition_line_id

        for base_amount in list(set(self.l10n_ar_withholding_ids.mapped('base_amount'))):
            withholding_lines = self.l10n_ar_withholding_ids.filtered(lambda x: x.base_amount == base_amount)
            nice_base_label = ','.join(withholding_lines.filtered('name').mapped('name'))
            account_id = self.company_id.l10n_ar_tax_base_account_id.id
            base_amount = sign * base_amount
            base_amount_currency = self.currency_id.round(base_amount / conversion_rate)
            write_off_line_vals.append({
                **self._get_withholding_move_line_default_values(),
                'name': _('Base Ret: ') + nice_base_label,
                # 'tax_ids': [Command.set(withholding_lines.mapped('tax_id').ids)],
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

    def write(self, vals):
        # OVERRIDE
        # vals_copy = vals.copy()
        l10n_ar_withholding_vals = {}
        if 'l10n_ar_withholding_ids' in vals and not self._context.get('skip_invoice_sync'):
            l10n_ar_withholding_vals = {'l10n_ar_withholding_ids': vals.pop('l10n_ar_withholding_ids')}
        import pdb; pdb.set_trace()
        if l10n_ar_withholding_vals:
            res = super().with_context(skip_account_move_synchronization=True, skip_invoice_sync=True, check_move_validity=False).write(l10n_ar_withholding_vals)
            self._synchronize_to_moves({'l10n_ar_withholding_ids'})
        else:
            res = super().write(vals)
        # self.with_context(l10n_ar_withholding_vals=l10n_ar_withholding_vals)._synchronize_to_moves(set(vals.keys()))
        return res

    def action_post(self):
        for line in self.l10n_ar_withholding_ids:
            if (not line.name or line.name == '/'):
                if line.tax_id.l10n_ar_withholding_sequence_id:
                    line.name = line.tax_id.l10n_ar_withholding_sequence_id.next_by_id()
                else:
                    raise UserError(_('Please enter withholding number for tax %s or configure a sequence on that tax') % line.tax_id.name)

        return super().action_post()
        #     elif not line.name:
        #         line.name = '/'

        # without_number = self.filtered(lambda x: x.tax_withholding_id and not x.withholding_number)

        # without_sequence = without_number.filtered(
        #     lambda x: not x.tax_withholding_id.withholding_sequence_id)
        # if without_sequence:
        #     raise UserError(_(
        #         'No puede validar pagos con retenciones que no tengan número '
        #         'de retención. Recomendamos agregar una secuencia a los '
        #         'impuestos de retención correspondientes. Id de pagos: %s') % (
        #         without_sequence.ids))

        # # a los que tienen secuencia les setamos el numero desde secuencia
        # for payment in (without_number - without_sequence):
        #     payment.withholding_number = \
        #         payment.tax_withholding_id.withholding_sequence_id.next_by_id()

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ('l10n_ar_withholding_ids',)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super()._prepare_move_line_default_vals(write_off_line_vals)
        import pdb; pdb.set_trace()
        # for line in res:
        #     if res['account_id'] in wittholding_accounts:
        #         res.pop()
        res += self._prepare_witholding_write_off_vals()
        wth_balance = sum(self.l10n_ar_withholding_ids.mapped('balance'))
        wth_amount_currency = sum(self.l10n_ar_withholding_ids.mapped('amount_currency'))

        # tratamos de recomponer el coutnerpart balance tal como lo hace odoo pero sin tener en cuenta las lineas de
        # retenciones que ya fueron creadas anteriormente y que pueden estar siendo modificadas
        write_off_line_vals_list = write_off_line_vals or []
        # TODO podriamos hacer browse del tax para otros casos como los que se se hace descuento por pago adelantado con impuesto
        # pero que la verdad no es aplicable a argentina. si hacemos browse luego verificariamos que sea de tipo retencion
        write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list if not x.get('tax_line_id'))
        write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)
        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
        else:
            liquidity_amount_currency = 0.0
        liquidity_balance = self.currency_id._convert(
            liquidity_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        counterpart_balance = -liquidity_balance - write_off_balance + wth_balance
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency - wth_amount_currency
        # liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
        # counterpart_lines.write({
        #     'balance': - (sum(liquidity_lines.mapped('balance')) + withholding_amount),
        #     'amount_currency': - (sum(liquidity_lines.mapped('balanceamount_currency')) + withholding_amount),
        # })


        # TODO: EVALUAR
        # si cambio el valor de la cuenta de liquidez quitando las retenciones el campo amount representa el monto que cancelo de la deuda
        # si cambio la cuenta de contraparte (agregando retenciones) el campo amount representa el monto neto que abono al partner
        # Ambos caminos funcionan pero no se cual es mejor a nivel usabilidad. depende como realizemos el calculo automatico de la ret
        # liquidity_accounts = [x.id for x in self._get_valid_liquidity_accounts() if x]
        valid_account_types = self._get_valid_payment_account_types()

        # no podemos usar lo que viene en la line de counterpart como valor porque ya trae restadas las retenciones anteriores.
        # entonces obtenemos el total a traves de la liquidity line y le sumamos las retenciones
        # liquidity_lines_vals = [line for line in res if line['account_id'] in self._get_valid_liquidity_accounts().ids]
        # debit = sum([line['debit'] for line in liquidity_lines_vals])
        # credit = sum([line['credit'] for line in liquidity_lines_vals])
        # amount_currency = sum([line['amount_currency'] for line in liquidity_lines_vals])

        for line in res:
            account_id = self.env['account.account'].browse(line['account_id'])
            if account_id.account_type in valid_account_types:
                # balance = debit - credit
                # balance += wth_balance
                # amount_currency = line['amount_currency'] + amount_currency
                line['debit'] = counterpart_balance if counterpart_balance > 0.0 else 0.0
                line['credit'] = -counterpart_balance if counterpart_balance < 0.0 else 0.0
                line['amount_currency'] = counterpart_amount_currency if counterpart_amount_currency < 0.0 else 0.0
                
        # 'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
        #         line
        #         if line['credit']:
        #             line['credit'] = liquidity_lines_vals - wth_balance
        #             line['amount_currency'] = wth_balance
        #         elif line['debit']:
        #             line['debit'] = liquidity_lines_vals + wth_balance
        #             line['amount_currency'] += wth_balance
                # deberia haber solo una, si se empiezan a soportar mas de una necesitamos otro approach o al menso va a funcionar y se lo vamos a sumar a la primera
                break
        import pdb; pdb.set_trace()
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
            for line in rec.matched_move_line_ids.with_context(payment_group_id=rec.id):
                invoice = line.move_id
                factor = invoice and invoice._get_tax_factor() or 1.0
                # TODO implementar
                matched_amount_untaxed += line.payment_group_matched_amount * factor
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

    @api.depends(
        'payment_ids.tax_withholding_id',
        'payment_ids.amount',
    )
    def _compute_withholdings_amount(self):
        for rec in self:
            rec.withholdings_amount = sum(
                rec.payment_ids.filtered(lambda x: x.tax_withholding_id).mapped('amount'))

    def compute_withholdings(self):
        for rec in self:
            if rec.partner_type != 'supplier':
                continue
            # limpiamos el type por si se paga desde factura ya que el en ese
            # caso viene in_invoice o out_invoice y en search de tax filtrar
            # por impuestos de venta y compra (y no los nuestros de pagos
            # y cobros)
            taxes = self.env['account.tax'].with_context(type=None).search([
                    ('type_tax_use', '=', 'none'),
                    ('l10n_ar_withholding_payment_type', '=', rec.partner_type),
                    ('company_id', '=', rec.company_id.id),
                ])
            for tax in taxes:
                rec.create_payment_withholdings(tax)

    def create_payment_withholdings(self, tax):
        self.ensure_one()
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

        payment_withholding = self.l10n_ar_withholding_ids.filtered(lambda x: x.tax_line_id == tax)
        if not computed_withholding_amount:
            # if on refresh no more withholding, we delete if it exists
            if payment_withholding:
                payment_withholding.unlink()
            return

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
            payment_withholding.write(vals)
        else:
            # TODO implementar devoluciones de retenciones
            # TODO en vez de pasarlo asi usar un command create
            vals['payment_id'] = self.id
            payment_withholding = payment_withholding.create(vals)

    # esto por ahora no tendria sentido
    # def confirm(self):
    #     res = super(AccountPaymentGroup, self).confirm()
    #     for rec in self:
    #         if rec.company_id.automatic_withholdings:
    #             rec.compute_withholdings()
    #     return res

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
                    withholdable_advanced_amount = self.unmatched_amount * (
                        self.withholdable_advanced_amount /
                        self.unreconciled_amount)
                else:
                    withholdable_advanced_amount = self.unmatched_amount
            else:
                withholdable_advanced_amount = \
                    self.withholdable_advanced_amount
        return (withholdable_advanced_amount, withholdable_invoiced_amount)
