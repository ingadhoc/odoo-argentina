# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import datetime


class AccountTax(models.Model):
    _inherit = "account.tax"

    withholding_type = fields.Selection(
        selection_add=([
            ('arba_ws', 'WS Arba'),
            ('tabla_ganancias', 'Tabla Ganancias'),
        ])
    )

    @api.multi
    def get_period_payments_domain(self, payment_group):
        previos_payment_groups_domain, previos_payments_domain = super(
            AccountTax, self).get_period_payments_domain(payment_group)
        if self.withholding_type == 'tabla_ganancias':
            previos_payment_groups_domain += [
                ('regimen_ganancias_id', '=',
                    payment_group.regimen_ganancias_id.id)]
            previos_payments_domain += [
                ('payment_group_id.regimen_ganancias_id', '=',
                    payment_group.regimen_ganancias_id.id)]
        return (
            previos_payment_groups_domain,
            previos_payments_domain)

    @api.multi
    def get_withholding_vals(self, payment_group):
        vals = super(AccountTax, self).get_withholding_vals(
            payment_group)
        base_amount = vals['withholdable_base_amount']
        commercial_partner = payment_group.commercial_partner_id
        if self.withholding_type == 'arba_ws':
            if commercial_partner.gross_income_type == 'no_liquida':
                vals['period_withholding_amount'] = 0.0
            else:
                payment_date = (
                    payment_group.payment_date and fields.Date.from_string(
                        payment_group.payment_date) or
                    datetime.date.today())
                alicuota = commercial_partner.get_arba_alicuota_retencion(
                    payment_group.company_id,
                    payment_date,
                )
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
                raise UserError(
                    'El partner %s no tiene configurada inscripcion en '
                    'impuesto a las ganancias' % commercial_partner.name)
            elif imp_ganancias_padron == 'EX':
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
            elif imp_ganancias_padron == 'NC':
                # no corresponde, no impuesto
                amount = 0.0
            # TODO, tal vez sea mejor utilizar otro campo?
            vals['communication'] = "%s - %s" % (
                regimen.codigo_de_regimen, regimen.concepto_referencia)
            vals['period_withholding_amount'] = amount
        return vals

    @api.v8
    def compute_all(
            self, price_unit, currency=None, quantity=1.0, product=None,
            partner=None):
        # ver nota en get_taxes_values
        try:
            date_invoice = self._context.date_invoice
            invoice_company = self._context.invoice_company
            partner = partner.with_context(
                invoice_company=invoice_company, date_invoice=date_invoice)
        except Exception:
            pass
        return super(AccountTax, self).compute_all(
            price_unit, currency=currency, quantity=quantity, product=product,
            partner=partner)

    def _compute_amount(
            self, base_amount, price_unit, quantity=1.0, product=None,
            partner=None):
        # ver nota en get_taxes_values
        try:
            date_invoice = self._context.date_invoice
            invoice_company = self._context.invoice_company
            partner = partner.with_context(
                invoice_company=invoice_company, date_invoice=date_invoice)
        except Exception:
            pass
        return super(AccountTax, self)._compute_amount(
            base_amount, price_unit, quantity=quantity, product=product,
            partner=partner)
