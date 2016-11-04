# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import datetime
import calendar
import base64
import re
from dateutil.relativedelta import relativedelta
from openerp import api, fields, models, _
from openerp.exceptions import Warning


class account_debt_report_wizard(models.TransientModel):
    _name = 'l10n_ar_account_withholding.sicore_wizard'
    _description = 'Account Withholding Export to SICORE Wizard'

    def _default_from_date(self):
        currdate = datetime.date.today()
        if currdate.day > 15:
            return currdate.strftime('%Y-%m-01')
        else:
            return (currdate+relativedelta(months=-1)).strftime('%Y-%m-16')

    def _default_to_date(self):
        currdate = datetime.date.today()
        if currdate.day > 15:
            return currdate.strftime('%Y-%m-15')
        else:
            dt = currdate+relativedelta(months=-1)
            mr = calendar.monthrange(dt.year, dt.month)
            return dt.strftime('%Y-%m-') + '%02d' % mr[1]

    from_date = fields.Date(
        'From',
        default=_default_from_date)

    to_date = fields.Date(
        'To',
        default=_default_to_date)

    company_id = fields.Many2one(
        'res.company', 
        'Company',
        default=lambda self: self.env.user.company_id,
        required=True)

    tax_withholding_type = fields.Selection(
        [('receipt', 'Receipt'), ('payment', 'Payment')],
        default='payment')

    tax_withholding_id = fields.Many2one(
        'account.tax.withholding',
        string='Withholding Tax')

    withholding_ids = fields.Many2many(
        comodel_name='account.voucher.withholding',
        relation='account_voucher_withholding_sicore_wizard_rel',
        column1='wizard_id', column2='withholding_id',
        string='Withholdings',
        compute='_compute_withholding_ids',
        readonly=True)

    txt_filename = fields.Char()
    txt_binary = fields.Binary()

    @api.onchange('company_id', 'tax_withholding_type')
    def _update_fields_domain(self):
        tax_domain = [('company_id', '=', self.company_id.id)]
        if self.tax_withholding_type:
            tax_domain.append(('type_tax_use', 'in', ('all', self.tax_withholding_type)))
        return {
            'domain': {
                'tax_withholding_id': tax_domain
            }
        }

    @api.depends('company_id', 'tax_withholding_type', 'tax_withholding_id', 'to_date', 'from_date')
    def _compute_withholding_ids(self):
        self.ensure_one()
        # search withholdings
        domain = [('state', '=', 'posted'), ('company_id', '=', self.company_id.id)]
        if self.from_date:
            domain.append(('date', '>=', self.from_date))
        if self.to_date:
            domain.append(('date', '<=', self.to_date))
        if self.tax_withholding_type and self.tax_withholding_type != 'all':
            domain.append(('type', '=', self.tax_withholding_type))
        if self.tax_withholding_id:
            domain.append(('tax_withholding_id', '=', self.tax_withholding_id.id))
        self.withholding_ids = self.env['account.voucher.withholding'].search(domain)        

    @api.multi
    def confirm(self):
        self.ensure_one()
        # build txt file
        content = ''
        for wh in self.withholding_ids:
            # Codigo del Comprobante         [ 2]
            content += (wh.type == 'receipt' and '02') or (wh.type == 'payment' and '06') or '00'
            # Fecha Emision Comprobante      [10] (dd/mm/yyyy)
            content += fields.Date.from_string(wh.voucher_id.date).strftime('%d/%m/%Y')
            # Numbero Comprobante            [16]
            content += '%016d' % int(re.sub('[^0-9]', '', wh.voucher_id.document_number))
            # Importe Comprobante            [16]
            content += '%016.2f' % wh.withholdable_invoiced_amount
            # Codigo de Impuesto             [ 3]
            content += '%03d' % wh.tax_withholding_id.tax_code_id.afip_code
            # Codigo de Regimen              [ 3]
            content += wh.voucher_id.regimen_ganancias_id and '%03d' % int(wh.voucher_id.regimen_ganancias_id.codigo_de_regimen) or '000'
            # Codigo de Operacion            [ 1]
            content += '1' # TODO: ????
            # Base de Calculo                [14]
            content += '%014.2f' % wh.withholdable_base_amount
            # Fecha Emision Retencion        [10] (dd/mm/yyyy)
            content += fields.Date.from_string(wh.date).strftime('%d/%m/%Y')
            # Codigo de Condicion            [ 2]
            content += '01' # TODO: ????
            # Retención Pract. a Suj. ..     [ 1]
            content += '0' # TODO: ????
            # Importe de Retencion           [14]
            content += '%014.2f' % wh.amount
            # Porcentaje de Exclusion        [ 6]
            content += '000.00' # TODO: ????
            # Fecha Emision Boletin          [10] (dd/mm/yyyy)
            content += fields.Date.from_string(wh.date).strftime('%d/%m/%Y')
            # Tipo Documento Retenido        [ 2]
            content += '%02d' % wh.partner_id.document_type_id.afip_code
            # Numero Documento Retenido      [20]
            content += wh.partner_id.document_number.ljust(20)
            # Numero Certificado Original    [14]
            content += '%014d' % 0 # TODO: ????

            content += '\r\n'
        # save file
        self.write({
            'txt_filename': 'SICORE_%s_%s_%s.txt' % (re.sub('[^\d\w]', '', self.company_id.name), self.from_date, self.to_date),
            'txt_binary': base64.encodestring(content)
        })
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'res_model': 'l10n_ar_account_withholding.sicore_wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref('l10n_ar_account_withholding.sicore_wizard_form_download').id,
            'context': self.env.context,
            'target': 'new',
        }
