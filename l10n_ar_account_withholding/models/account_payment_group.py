# -*- coding: utf-8 -*-
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

    @api.multi
    def onchange(self, values, field_name, field_onchange):
        """
        Idea obtenida de aca
        https://github.com/odoo/odoo/issues/16072#issuecomment-289833419
        por el cambio que se introdujo en esa mimsa conversación, TODO en v11
        no haría mas falta, simplemente domain="[('id', 'in', x2m_field)]"
        Otras posibilidades que probamos pero no resultaron del todo fue:
        * agregar onchange sobre campos calculados y que devuelvan un dict con
        domain. El tema es que si se entra a un registro guardado el onchange
        no se ejecuta
        * usae el modulo de web_domain_field que esta en un pr a la oca
        """
        for field in field_onchange.keys():
            if field.startswith('company_regimenes_ganancias_ids.'):
                del field_onchange[field]
        return super(AccountPaymentGroup, self).onchange(
            values, field_name, field_onchange)

    @api.multi
    @api.depends('company_id.regimenes_ganancias_ids')
    def _company_regimenes_ganancias(self):
        """
        Lo hacemos con campo computado y no related para que solo se setee
        y se exija si es pago de o a proveedor
        """
        for rec in self.filtered(lambda x: x.partner_type == 'supplier'):
            rec.company_regimenes_ganancias_ids = (
                rec.company_id.regimenes_ganancias_ids)

    @api.onchange('retencion_ganancias', 'commercial_partner_id')
    def change_retencion_ganancias(self):
        def_regimen = False
        if self.retencion_ganancias == 'nro_regimen':
            cia_regs = self.company_regimenes_ganancias_ids
            partner_regimen = (
                self.commercial_partner_id.default_regimen_ganancias_id)
            if partner_regimen and partner_regimen in cia_regs:
                def_regimen = partner_regimen
            elif cia_regs:
                def_regimen = cia_regs[0]
        self.regimen_ganancias_id = def_regimen

    @api.onchange('company_regimenes_ganancias_ids')
    def change_company_regimenes_ganancias(self):
        # partner_type == 'supplier' ya lo filtra el company_regimenes_ga...
        if self.company_regimenes_ganancias_ids:
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
