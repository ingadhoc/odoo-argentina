# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields


class AccountVoucher(models.Model):

    _inherit = "account.voucher"

    # @api.model
    # def _get_regimen_ganancias(self):
    #     result = []
    #     for line in self.
    #     return

    retencion_ganancias = fields.Selection([
        # _get_regimen_ganancias,
        ('imposibilidad_retencion', 'Imposibilidad de Retención'),
        ('no_aplica', 'No Aplica'),
        ('nro_regimen', 'Nro Regimen'),
    ],
        'Retención Ganancias',
        readonly=True,
        states={'draft': [('readonly', False)],
                'confirmed': [('readonly', False)]}
    )
    regimen_ganancias_id = fields.Many2one(
        'afip.tabla_ganancias.alicuotasymontos',
        'Regimen Ganancias',
        readonly=True,
        states={'draft': [('readonly', False)],
                'confirmed': [('readonly', False)]}
    )
    company_regimenes_ganancias_ids = fields.Many2many(
        related='company_id.regimenes_ganancias_ids',
        readonly=True,
    )

    @api.onchange('retencion_ganancias')
    def change_retencion_ganancias(self):
        if self.retencion_ganancias == 'nro_regimen':
            self.regimen_ganancias_id = self.company_regimenes_ganancias_ids[0]
        else:
            self.regimen_ganancias_id = False

    @api.onchange('company_regimenes_ganancias_ids')
    def change_company_regimenes_ganancias(self):
        if self.company_regimenes_ganancias_ids and self.type == 'payment':
            self.retencion_ganancias = 'nro_regimen'

    @api.multi
    def compute_withholdings(self):
        for voucher in self:
            self.env['account.tax.withholding'].search([
                ('type_tax_use', 'in', [self.type, 'all']),
                ('company_id', '=', self.company_id.id),
            ]).create_voucher_withholdings(voucher)

    @api.multi
    def action_confirm(self):
        res = super(AccountVoucher, self).action_confirm()
        self.search([
            ('type', '=', 'payment'),
            ('journal_id.automatic_withholdings', '=', True),
            ('id', 'in', self.ids),
        ]).compute_withholdings()
        return res
