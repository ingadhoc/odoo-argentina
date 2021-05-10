from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class AccountTax(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(
        selection_add=([
            ('partner_tax', 'Alícuota en el Partner'),
        ])
    )
    withholding_type = fields.Selection(
        selection_add=([
            ('tabla_ganancias', 'Tabla Ganancias'),
            ('partner_tax', 'Alícuota en el Partner'),
        ])
    )
    # default_alicuot = fields.Float(
    #     'Alícuota por defecto',
    #     help="Alícuota por defecto para los partners que no figuran en el "
    #     "padrón"
    # )
    # default_alicuot_copy = fields.Float(
    #     related='default_alicuot',
    # )

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

    def get_period_payments_domain(self, payment_group):
        previos_payment_groups_domain, previos_payments_domain = super(
            AccountTax, self).get_period_payments_domain(payment_group)
        if self.withholding_type == 'tabla_ganancias' and payment_group.retencion_ganancias == 'nro_regimen' \
           and payment_group.regimen_ganancias_id:
            previos_payment_groups_domain += [
                ('regimen_ganancias_id', '=', payment_group.regimen_ganancias_id.id),
                ('retencion_ganancias', '=', 'nro_regimen'),
            ]
            previos_payments_domain += [
                ('payment_group_id.regimen_ganancias_id', '=', payment_group.regimen_ganancias_id.id),
                ('payment_group_id.retencion_ganancias', '=', 'nro_regimen'),
            ]
        return (
            previos_payment_groups_domain,
            previos_payments_domain)

    def get_withholding_vals(self, payment_group):
        commercial_partner = payment_group.commercial_partner_id

        force_withholding_amount_type = None
        if self.withholding_type == 'partner_tax':
            alicuot_line = self.get_partner_alicuot(
                commercial_partner,
                payment_group.payment_date or fields.Date.context_today(self),
            )
            alicuota = alicuot_line.alicuota_retencion / 100.0
            force_withholding_amount_type = alicuot_line.withholding_amount_type

        vals = super(AccountTax, self).get_withholding_vals(
            payment_group, force_withholding_amount_type)
        base_amount = vals['withholdable_base_amount']

        if self.withholding_type == 'partner_tax':
            amount = base_amount * (alicuota)
            vals['comment'] = "%s x %s" % (
                base_amount, alicuota)
            vals['period_withholding_amount'] = amount
        elif self.withholding_type == 'tabla_ganancias':
            regimen = payment_group.regimen_ganancias_id
            imp_ganancias_padron = commercial_partner.imp_ganancias_padron
            if (
                    payment_group.retencion_ganancias != 'nro_regimen' or
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
                    escala = self.env['afip.tabla_ganancias.escala'].search([
                        ('importe_desde', '<=', base_amount),
                        ('importe_hasta', '>', base_amount),
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
            vals['communication'] = "%s - %s" % (
                regimen.codigo_de_regimen, regimen.concepto_referencia)
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
            from_date = date + relativedelta(day=1)
            to_date = date + relativedelta(day=1, days=-1, months=+1)

            agip_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_901')
            arba_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_902')
            cdba_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_904')
            invoice_tags = self.invoice_repartition_line_ids.mapped('tag_ids')

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
            self, base_amount, price_unit, quantity=1.0, product=None,
            partner=None):
        if self.amount_type == 'partner_tax':
            date = self._context.get('invoice_date', fields.Date.context_today(self))
            partner = partner and partner.sudo()
            return base_amount * self.sudo().get_partner_alicuota_percepcion(partner, date)
        else:
            return super(AccountTax, self)._compute_amount(
                base_amount, price_unit, quantity, product, partner)
