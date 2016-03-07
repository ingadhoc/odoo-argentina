# -*- coding: utf-8 -*-
from openerp import models, fields, api
import datetime


class AccountTaxWithholding(models.Model):
    _inherit = "account.tax.withholding"

    automatic_method = fields.Selection(
        selection_add=([('arba_ws', 'WS Arba')])
        )

    @api.multi
    def create_voucher_withholdings(self, voucher):
        for tax in self:
            if tax.automatic_method == 'arba_ws':
                date = (
                    voucher.date and fields.Date.from_string(voucher.date) or
                    datetime.date.today())
                arba_data = self.company_id.get_arba_data(
                    voucher.partner_id.commercial_partner_id,
                    date
                    )
                AlicuotaRetencion = arba_data.get('AlicuotaRetencion')
                if AlicuotaRetencion:
                    alicuot = float(AlicuotaRetencion.replace(',', '.'))
                    self.env['account.voucher.withholding'].create({
                        'amount': voucher.amount * alicuot,
                        'voucher_id': voucher.id,
                        'tax_withholding_id': tax.id,
                        })
                    # TODO descontar del monto lo que tenemos que tener
        return super(AccountTaxWithholding, self).create_voucher_withholdings(
            voucher)
