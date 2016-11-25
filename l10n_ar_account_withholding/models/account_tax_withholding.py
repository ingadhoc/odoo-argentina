# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import Warning
import datetime


class AccountTaxWithholding(models.Model):
    _inherit = "account.tax.withholding"

    type = fields.Selection(
        selection_add=([
            ('arba_ws', 'WS Arba'),
            ('tabla_ganancias', 'Tabla Ganancias'),
        ])
    )

    @api.multi
    def get_withholdable_factor(self, voucher_line):
        self.ensure_one()
        if self.base_amount_type == 'untaxed_amount':
            invoice = voucher_line.move_line_id.invoice
            doc_letter = invoice.afip_document_class_id.document_letter_id.name
            # if we receive B invoices, then we take out 21 of vat
            # this use of case if when company is except on vat for eg.
            if doc_letter == 'B':
                factor = 1.0 / 1.21
                return factor
        return super(AccountTaxWithholding, self).get_withholdable_factor(
            voucher_line)

    @api.multi
    def get_withholding_vals(self, voucher):
        vals = super(AccountTaxWithholding, self).get_withholding_vals(
            voucher)
        base_amount = vals['withholdable_base_amount']
        if self.type == 'arba_ws':
            if voucher.partner_id.gross_income_type == 'no_liquida':
                vals['period_withholding_amount'] = 0.0
            else:
                date = (
                    voucher.date and fields.Date.from_string(voucher.date) or
                    datetime.date.today())
                alicuota = voucher.partner_id.get_arba_alicuota_retencion(
                    voucher.company_id,
                    date,
                )
                amount = base_amount * (alicuota)
                vals['comment'] = "%s x %s" % (
                    base_amount, alicuota)
                vals['period_withholding_amount'] = amount
        elif self.type == 'tabla_ganancias':
            regimen = voucher.regimen_ganancias_id
            imp_ganancias_padron = voucher.partner_id.imp_ganancias_padron
            if voucher.retencion_ganancias != 'nro_regimen' or not regimen:
                # if amount zero then we dont create withholding
                amount = 0.0
            elif not imp_ganancias_padron:
                raise Warning(
                    'El partner %s no tiene configurada inscripcion en '
                    'impuesto a las ganancias' % voucher.partner_id.name)
            elif imp_ganancias_padron == 'EX':
                # if amount zero then we dont create withholding
                amount = 0.0
            # TODO validar excencion actualizada
            elif imp_ganancias_padron == 'AC':
                # alicuota inscripto
                non_taxable_amount = (
                    regimen.montos_no_sujetos_a_retencion)
                vals['non_taxable_amount'] = non_taxable_amount
                if base_amount < non_taxable_amount:
                    base_amount = 0.0
                else:
                    base_amount -= non_taxable_amount
                vals['withholdable_base_amount'] = base_amount
                if regimen.porcentaje_inscripto == -1:
                    escala = self.env['afip.tabla_ganancias.escala'].search([
                        ('importe_desde', '<', base_amount),
                        ('importe_hasta', '>=', base_amount),
                    ], limit=1)
                    if not escala:
                        raise Warning(
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
            vals['description'] = regimen.codigo_de_regimen
            vals['period_withholding_amount'] = amount
        return vals
