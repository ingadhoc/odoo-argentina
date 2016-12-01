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
        ondelete='restrict',
        states={'draft': [('readonly', False)],
                'confirmed': [('readonly', False)]}
    )
    company_regimenes_ganancias_ids = fields.Many2many(
        related='company_id.regimenes_ganancias_ids',
        readonly=True,
    )
    # For new API onchange
    partner_id_copy = fields.Many2one(
        related='partner_id'
    )

    @api.onchange('retencion_ganancias', 'partner_id_copy')
    def change_retencion_ganancias(self):
        def_regimen = False
        if self.retencion_ganancias == 'nro_regimen':
            cia_regs = self.company_regimenes_ganancias_ids
            partner_regimen = self.partner_id.default_regimen_ganancias_id
            if partner_regimen and partner_regimen in cia_regs:
                def_regimen = partner_regimen
            elif cia_regs:
                def_regimen = cia_regs[0]
        self.regimen_ganancias_id = def_regimen

    @api.onchange('company_regimenes_ganancias_ids')
    def change_company_regimenes_ganancias(self):
        if self.company_regimenes_ganancias_ids and self.type == 'payment':
            self.retencion_ganancias = 'nro_regimen'

    @api.model
    def create(self, vals):
        """
        para casos donde se paga desde algun otro lugar (por ej. liquidador de
        impuestos), seteamos no aplica si no hay nada seteado
        """
        voucher = super(AccountVoucher, self).create(vals)
        if (
                voucher.company_regimenes_ganancias_ids and
                voucher.type == 'payment' and
                not voucher.retencion_ganancias and
                not voucher.regimen_ganancias_id):
            voucher.retencion_ganancias = 'no_aplica'
        return voucher
