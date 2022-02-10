##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class AccountPaymentGroup(models.Model):

    _inherit = "account.payment.group"

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
        'afip.tabla_ganancias.alicuotasymontos',
        compute='_company_regimenes_ganancias',
    )

    @api.depends('company_id.regimenes_ganancias_ids')
    def _company_regimenes_ganancias(self):
        """
        Lo hacemos con campo computado y no related para que solo se setee
        y se exija si es pago de o a proveedor
        """
        for rec in self:
            if rec.partner_type == 'supplier':
                rec.company_regimenes_ganancias_ids = rec.company_id.regimenes_ganancias_ids
            else:
                rec.company_regimenes_ganancias_ids = rec.env['afip.tabla_ganancias.alicuotasymontos']

    @api.onchange('commercial_partner_id')
    def change_retencion_ganancias(self):
        # si es exento en ganancias o no tiene clasificacion pero es monotributista, del exterior o consumidor final, sugerimos regimen no_aplica
        if self.commercial_partner_id.imp_ganancias_padron in ['EX', 'NC'] or (
            not self.commercial_partner_id.imp_ganancias_padron and
            self.commercial_partner_id.l10n_ar_afip_responsibility_type_id.code in ('5', '6', '9', '13')):
            self.retencion_ganancias = 'no_aplica'
            self.regimen_ganancias_id = False
        else:
            cia_regs = self.company_regimenes_ganancias_ids
            partner_regimen = (
                self.commercial_partner_id.default_regimen_ganancias_id)
            if partner_regimen:
                def_regimen = partner_regimen
            elif cia_regs:
                def_regimen = cia_regs[0]
            else:
                def_regimen = False
            self.regimen_ganancias_id = def_regimen

    @api.onchange('company_regimenes_ganancias_ids')
    def change_company_regimenes_ganancias(self):
        # partner_type == 'supplier' ya lo filtra el company_regimenes_ga...
        if self.commercial_partner_id.imp_ganancias_padron in ['EX', 'NC'] or (
            not self.commercial_partner_id.imp_ganancias_padron and
            self.commercial_partner_id.l10n_ar_afip_responsibility_type_id.code in ('5', '6', '9', '13')):
            self.retencion_ganancias = 'no_aplica'
            self.regimen_ganancias_id = False
        elif self.company_regimenes_ganancias_ids:
            self.retencion_ganancias = 'nro_regimen'

    # sacamos esto por ahora ya que no es muy prolijo y nos se esta usando, si
    # lo llegamos a activar entonces tener en cuenta que en sipreco no queremos
    # que en borrador se setee ninguna regimen de ganancias
    # @api.model
    # def create(self, vals):
    #     """
    #     para casos donde se paga desde algun otro lugar (por ej. liquidador
    #     de impuestos), seteamos no aplica si no hay nada seteado
    #     """
    #     payment_group = super(AccountPaymentGroup, self).create(vals)
    #     if (
    #             payment_group.company_regimenes_ganancias_ids and
    #             payment_group.partner_type == 'supplier' and
    #             not payment_group.retencion_ganancias and
    #             not payment_group.regimen_ganancias_id):
    #         payment_group.retencion_ganancias = 'no_aplica'
    #     return payment_group
