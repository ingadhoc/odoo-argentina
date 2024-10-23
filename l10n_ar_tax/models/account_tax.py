from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class AccountTax(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(
        selection_add=([
            ('partner_tax', 'Alícuota en el Partner'),
        ]), ondelete={'partner_tax': 'set default'}
    )
    withholding_type = fields.Selection(
        selection_add=([
            ('tabla_ganancias', 'Tabla Ganancias'),
            ('partner_tax', 'Alícuota en el Partner'),
        ]), ondelete={'tabla_ganancias': 'set default', 'partner_tax': 'set default'}
    )

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

    @api.constrains('amount_type', 'withholding_type')
    def check_partner_tax_tag(self):
        recs = self.filtered(lambda x: ((
            x.type_tax_use in ['sale', 'purchase'] and
            x.amount_type == 'partner_tax') or (
            x.type_tax_use in ['customer', 'supplier'] and
            x.withholding_type == 'partner_tax')) and not x.invoice_repartition_line_ids.mapped('tag_ids'))
        if recs:
            raise UserError(_(
                'Si utiliza Cálculo de impuestos igual a "Alícuota en el '
                'Partner", debe setear al menos una etiqueta en el impuesto y'
                ' utilizar esa misma etiqueta en las alícuotas configuradas en'
                ' el partner. Revise los impuestos con id: %s') % recs.ids)

    def get_period_payments_domain(self, payment):
        previous_payments_domain, previous_withholdings_domain = super(
            AccountTax, self).get_period_payments_domain(payment)
        if self.withholding_type == 'tabla_ganancias' and payment.retencion_ganancias == 'nro_regimen' \
           and payment.regimen_ganancias_id:
            previous_payments_domain += [
                ('regimen_ganancias_id', '=', payment.regimen_ganancias_id.id),
                ('retencion_ganancias', '=', 'nro_regimen'),
            ]
            previous_withholdings_domain += [
                ('payment_id.regimen_ganancias_id', '=', payment.regimen_ganancias_id.id),
                ('payment_id.retencion_ganancias', '=', 'nro_regimen'),
            ]
        return (
            previous_payments_domain,
            previous_withholdings_domain)

    def get_withholding_vals(self, payment):
        commercial_partner = payment.partner_id.commercial_partner_id

        force_withholding_amount_type = None
        if self.withholding_type == 'partner_tax':
            alicuot_line = self.get_partner_alicuot(
                commercial_partner,
                payment.date or fields.Date.context_today(self),
            )
            alicuota = alicuot_line.alicuota_retencion / 100.0
            force_withholding_amount_type = alicuot_line.withholding_amount_type

        vals = super(AccountTax, self).get_withholding_vals(
            payment, force_withholding_amount_type)
        base_amount = vals['withholdable_base_amount']

        if self.withholding_type == 'partner_tax':
            amount = base_amount * (alicuota)
            vals['comment'] = "%s x %s" % (
                base_amount, alicuota)
            vals['period_withholding_amount'] = amount
        elif self.withholding_type == 'tabla_ganancias':
            regimen = payment.regimen_ganancias_id
            imp_ganancias_padron = commercial_partner.imp_ganancias_padron
            if (
                    payment.retencion_ganancias != 'nro_regimen' or
                    not regimen):
                # if amount zero then we dont create withholding
                amount = 0.0
            elif not imp_ganancias_padron:
                raise UserError(_(
                    'El partner %s no tiene configurada inscripcion en '
                    'impuesto a las ganancias' % commercial_partner.name))
            elif imp_ganancias_padron in ['EX', 'NC']:
                # if amount zero then we dont create withholding
                amount = 0.0
            # TODO validar excencion actualizada
            elif imp_ganancias_padron == 'AC':
                # alicuota inscripto
                non_taxable_amount = (
                    regimen.montos_no_sujetos_a_retencion)
                vals['withholding_non_taxable_amount'] = non_taxable_amount
                if base_amount < non_taxable_amount:
                    base_amount = 0.0
                else:
                    base_amount -= non_taxable_amount
                vals['withholdable_base_amount'] = base_amount
                if regimen.porcentaje_inscripto == -1:
                    # hacemos <= porque si es 0 necesitamos que encuentre
                    # la primer regla (0 es en el caso en que la no
                    # imponible sea mayor)
                    codigo_de_regimen = '119' if regimen.codigo_de_regimen == '119' else False
                    escala = self.env['afip.tabla_ganancias.escala'].search([
                        ('importe_desde', '<=', base_amount),
                        ('importe_hasta', '>', base_amount),
                        ('codigo_de_regimen', '=', codigo_de_regimen)
                    ], limit=1)
                    if not escala:
                        raise UserError(
                            'No se encontro ninguna escala para el monto'
                            ' %s' % (base_amount))
                    amount = escala.importe_fijo
                    amount += (escala.porcentaje / 100.0) * (
                        base_amount - escala.importe_excedente)
                    vals['comment'] = "%s + (%s x %s)" % (
                        escala.importe_fijo,
                        base_amount - escala.importe_excedente,
                        escala.porcentaje / 100.0)
                else:
                    amount = base_amount * (
                        regimen.porcentaje_inscripto / 100.0)
                    vals['comment'] = "%s x %s" % (
                        base_amount, regimen.porcentaje_inscripto / 100.0)
            elif imp_ganancias_padron == 'NI':
                # alicuota no inscripto
                amount = base_amount * (
                    regimen.porcentaje_no_inscripto / 100.0)
                vals['comment'] = "%s x %s" % (
                    base_amount, regimen.porcentaje_no_inscripto / 100.0)
            # TODO, tal vez sea mejor utilizar otro campo?
            vals['ref'] = "%s - %s" % (regimen.codigo_de_regimen, regimen.concepto_referencia)
            vals['period_withholding_amount'] = amount
        return vals

    def get_partner_alicuota_percepcion(self, partner, date):
        if partner and date:
            arba = self.get_partner_alicuot(partner, date)
            return arba.alicuota_percepcion / 100.0
        return 0.0

    def get_partner_alicuot(self, partner, date):
        self.ensure_one()
        commercial_partner = partner.commercial_partner_id
        company = self.company_id
        alicuot = partner.arba_alicuot_ids.search([
            ('tag_id', 'in', self.invoice_repartition_line_ids.mapped('tag_ids').ids),
            ('company_id', '=', company.id),
            ('partner_id', '=', commercial_partner.id),
            '|',
            ('from_date', '=', False),
            ('from_date', '<=', date),
            '|',
            ('to_date', '=', False),
            ('to_date', '>=', date),
        ], limit=1)

        # solo buscamos en padron para estas responsabilidades
        if not alicuot and \
                commercial_partner.l10n_ar_afip_responsibility_type_id.code in \
                ['1', '1FM', '2', '3', '4', '6', '11', '13']:

            invoice_tags = self.invoice_repartition_line_ids.mapped('tag_ids')
            padron_file = self.env['res.company.jurisdiction.padron'].search([
                ('jurisdiction_id', 'in', invoice_tags.ids),
                ('company_id', '=', company.id),
                '|',
                ('l10n_ar_padron_from_date', '=', False),
                ('l10n_ar_padron_from_date', '<=', date),
                '|',
                ('l10n_ar_padron_to_date', '=', False),
                ('l10n_ar_padron_to_date', '>=', date),
            ], limit=1)
            from_date = date + relativedelta(day=1)
            to_date = date + relativedelta(day=1, days=-1, months=+1)

            agip_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_901')
            arba_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_902')
            cdba_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_904')
            if padron_file:
                nro, alicuot_ret, alicuot_per = padron_file._get_aliquit(commercial_partner)
                if nro:
                    return partner.arba_alicuot_ids.sudo().create({
                        'numero_comprobante': nro,
                        'alicuota_retencion': float(alicuot_ret),
                        'alicuota_percepcion': float(alicuot_per),
                        'partner_id': commercial_partner.id,
                        'company_id': company.id,
                        'tag_id': padron_file.jurisdiction_id.id,
                        'from_date': from_date,
                        'to_date': to_date,

                    })
            if arba_tag and arba_tag.id in invoice_tags.ids:
                arba_data = company.get_arba_data(
                    commercial_partner,
                    from_date, to_date,
                )
                # si no hay numero de comprobante entonces es porque no
                # figura en el padron, aplicamos alicuota no inscripto
                if not arba_data['numero_comprobante']:
                    arba_data['numero_comprobante'] = \
                        'Alícuota no inscripto'
                    arba_data['alicuota_retencion'] = \
                        company.arba_alicuota_no_sincripto_retencion
                    arba_data['alicuota_percepcion'] = \
                        company.arba_alicuota_no_sincripto_percepcion

                arba_data['partner_id'] = commercial_partner.id
                arba_data['company_id'] = company.id
                arba_data['tag_id'] = arba_tag.id
                arba_data['from_date'] = from_date
                arba_data['to_date'] = to_date
                alicuot = partner.arba_alicuot_ids.sudo().create(arba_data)
            elif agip_tag and agip_tag.id in invoice_tags.ids:
                agip_data = company.get_agip_data(
                    commercial_partner,
                    date,
                )
                # si no hay numero de comprobante entonces es porque no
                # figura en el padron, aplicamos alicuota no inscripto
                if not agip_data['numero_comprobante']:
                    agip_data['numero_comprobante'] = \
                        'Alícuota no inscripto'
                    agip_data['alicuota_retencion'] = \
                        company.agip_alicuota_no_sincripto_retencion
                    agip_data['alicuota_percepcion'] = \
                        company.agip_alicuota_no_sincripto_percepcion
                agip_data['from_date'] = from_date
                agip_data['to_date'] = to_date
                agip_data['partner_id'] = commercial_partner.id
                agip_data['company_id'] = company.id
                agip_data['tag_id'] = agip_tag.id
                alicuot = partner.arba_alicuot_ids.sudo().create(agip_data)
            elif cdba_tag and cdba_tag.id in invoice_tags.ids:
                cordoba_data = company.get_cordoba_data(
                    commercial_partner,
                    date,
                )
                cordoba_data['from_date'] = from_date
                cordoba_data['to_date'] = to_date
                cordoba_data['partner_id'] = commercial_partner.id
                cordoba_data['company_id'] = company.id
                cordoba_data['tag_id'] = cdba_tag.id
                alicuot = partner.arba_alicuot_ids.sudo().create(cordoba_data)
        return alicuot

    def _compute_amount(
            self, base_amount, price_unit, quantity=1.0, product=None, partner=None, fixed_multiplicator=1):
        if self.amount_type == 'partner_tax':
            date = self._context.get('invoice_date') or fields.Date.context_today(self)
            partner = partner and partner.sudo()
            return base_amount * self.sudo().get_partner_alicuota_percepcion(partner, date)
        else:
            return super(AccountTax, self)._compute_amount(
                base_amount, price_unit, quantity=quantity, product=product,
                partner=partner, fixed_multiplicator=fixed_multiplicator)
