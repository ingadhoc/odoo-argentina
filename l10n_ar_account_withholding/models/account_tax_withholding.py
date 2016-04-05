# -*- coding: utf-8 -*-
from openerp import models, fields, api
import datetime


# class AccountTaxWithholdingProfitTable(models.Model):
    # profits_table = fields.One2many(
        # )
    # amount_from
    # amount_to
    # withholding_amount
    # plus_percentage
    # sobre excedente (calculado)?

class AccountTaxWithholding(models.Model):
    _inherit = "account.tax.withholding"

    # TODO lo necesitamos?
    # regime_code = fields.Char(
    #     'Cód. Régimen'
    #     )
    type = fields.Selection(
        selection_add=([('arba_ws', 'WS Arba')])
        )

    @api.multi
    def get_withholding_vals(self, voucher):
        vals = super(AccountTaxWithholding, self).get_withholding_vals(
            voucher)
        if self.type == 'arba_ws':
            date = (
                voucher.date and fields.Date.from_string(voucher.date) or
                datetime.date.today())
            arba_data = self.company_id.get_arba_data(
                voucher.partner_id.commercial_partner_id,
                date
                )
            AlicuotaRetencion = arba_data.get('AlicuotaRetencion')
            if not AlicuotaRetencion:
                return {}
            alicuot = float(AlicuotaRetencion.replace(',', '.'))
            amount = vals['withholdable_base_amount'] * alicuot
            vals['amount'] = amount
            vals['suggested_withholding_amount'] = amount
            vals['comment'] = arba_data
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
