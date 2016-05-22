# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import datetime


class AccountTaxWithholding(models.Model):
    _inherit = "account.tax.withholding"

    # TODO lo necesitamos?
    # regime_code = fields.Char(
    #     'Cód. Régimen'
    #     )
    type = fields.Selection(
        selection_add=([
            ('arba_ws', 'WS Arba'),
            ('tabla_ganancias', 'Tabla Ganancias'),
        ])
    )

    @api.multi
    def get_withholding_vals(self, voucher):
        vals = super(AccountTaxWithholding, self).get_withholding_vals(
            voucher)
        base_amount = vals['withholdable_base_amount']
        if self.type == 'arba_ws':
            if voucher.partner_id.gross_income_type == 'no_liquida':
                vals['amount'] = 0.0
            else:
                date = (
                    voucher.date and fields.Date.from_string(voucher.date) or
                    datetime.date.today())
                arba_data = self.company_id.get_arba_data(
                    voucher.partner_id.commercial_partner_id,
                    date
                )
                AlicuotaRetencion = arba_data.get('AlicuotaRetencion')
                if not AlicuotaRetencion:
                    raise Warning('No pudimos obtener la AlicuotaRetencion')
                alicuot = float(AlicuotaRetencion.replace(',', '.'))
                amount = base_amount * alicuot
                vals['amount'] = amount
                vals['computed_withholding_amount'] = amount
                vals['comment'] = arba_data
        elif self.type == 'tabla_ganancias':
            # if not self.company_id.regimenes_ganancias:
            #     raise Warning(
            #         'No hay regimenes de ganancias configurados para la '
            #         'compania %s' % self.company_id.name)
            # TODO, por ahora tomamos el primero pero hay que definir cual va
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
                raise Warning('Exentos no implementado!')
            # TODO validar excencion actualizada
            elif imp_ganancias_padron == 'AC':
                # alicuota inscripto
                # vals['non_taxable_minimum'] = (
                vals['non_taxable_amount'] = (
                    regimen.montos_no_sujetos_a_retencion)
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
                else:
                    amount = base_amount * (
                        regimen.porcentaje_inscripto / 100.0)
            elif imp_ganancias_padron == 'NI':
                # alicuota no inscripto
                amount = base_amount * (
                    regimen.porcentaje_no_inscripto / 100.0)
            elif imp_ganancias_padron == 'NC':
                # no corresponde, no impuesto
                amount = 0.0
            vals['description'] = regimen.codigo_de_regimen
            vals['amount'] = amount
            vals['computed_withholding_amount'] = amount
            # self.env[].search('code')
        return vals


#     @api.multi
#     def get_period_withholding_amount(self, base_amount, voucher):
#         self.ensure_one()
#         if self.type == 'arba_ws':
#             date = (
#                 voucher.date and fields.Date.from_string(voucher.date) or
#                 datetime.date.today())
#             arba_data = self.company_id.get_arba_data(
#                 voucher.partner_id.commercial_partner_id,
#                 date
#                 )
#             AlicuotaRetencion = arba_data.get('AlicuotaRetencion')
#             if AlicuotaRetencion:
#                 alicuot = float(AlicuotaRetencion.replace(',', '.'))
#                 return base_amount * alicuot
#         return super(
#             AccountTaxWithholding, self).get_period_withholding_amount(
#                 base_amount)
# {'GrupoRetencion': '3', 'NumeroComprobante': '82257338', 'GrupoPercepcion': '5', 'AlicuotaPercepcion': '0,30', 'CodigoHash': '26fa6202134dd758366f7a79ae9b8569', 'CuitContribuyente': '30714517682', 'AlicuotaRetencion': '0,20'}
    # @api.multi
    # def create_voucher_withholdings(self, voucher):
    #     for tax in self:
    #         if tax.automatic_method == 'arba_ws':
    #             date = (
    #                 voucher.date and fields.Date.from_string(voucher.date) or
    #                 datetime.date.today())
    #             arba_data = self.company_id.get_arba_data(
    #                 voucher.partner_id.commercial_partner_id,
    #                 date
    #                 )
    #             AlicuotaRetencion = arba_data.get('AlicuotaRetencion')
    #             if AlicuotaRetencion:
    #                 alicuot = float(AlicuotaRetencion.replace(',', '.'))
    #                 self.env['account.voucher.withholding'].create({
    #                     'amount': voucher.amount * alicuot,
    #                     'voucher_id': voucher.id,
    #                     'tax_withholding_id': tax.id,
    #                     })
    #                 # TODO descontar del monto lo que tenemos que tener
    #     return super(AccountTaxWithholding, self).create_voucher_withholdings(
    #         voucher)
