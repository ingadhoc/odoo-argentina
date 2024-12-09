##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class AccountPayment(models.Model):

    _inherit = "account.payment"

    retencion_ganancias = fields.Selection([
        # _get_regimen_ganancias,
        ('imposibilidad_retencion', 'Imposibilidad de Retención'),
        ('no_aplica', 'No Aplica'),
        ('nro_regimen', 'Nro Regimen'),
    ],
        'Retención Ganancias',
    )
    regimen_ganancias_id = fields.Many2one(
        'afip.tabla_ganancias.alicuotasymontos',
        'Regimen Ganancias',
        ondelete='restrict',
    )
    company_regimenes_ganancias_ids = fields.Many2many(
        'afip.tabla_ganancias.alicuotasymontos',
        compute='_company_regimenes_ganancias',
    )
    need_withholding_recompute = fields.Boolean(
        compute="_compute_need_withholding_recompute",
        store=True,
        readonly=False
    )

    @api.depends('withholdable_advanced_amount', 'regimen_ganancias_id', 'retencion_ganancias', 'date', 'unreconciled_amount', 'to_pay_move_line_ids')
    def _compute_need_withholding_recompute(self):
        for rec in self:
            rec.need_withholding_recompute = False
            if rec.partner_type == 'supplier' and rec.env['account.tax'].with_context(type=None).search([
                ('type_tax_use', '=', 'none'),
                ('withholding_type', '!=', 'none'),
                ('l10n_ar_withholding_payment_type', '=', rec.partner_type),
                ('company_id', '=', rec.company_id.id),
            ], limit=1):
                rec.need_withholding_recompute = True

    def compute_withholdings(self):
        super().compute_withholdings()
        self.need_withholding_recompute = False

    # estaria bueno re-incorporarlo pero para hacerlo:
    # a) tenemos que ver que cuando creamos pago desde factura ya viaje la retencion de ganancias o convertirlas en campos calculados con pre compute?
    # el tema es que no termina computando regimen de ganancias porque en "regimen = payment.regimen_ganancias_id" llega vacio
    # b) ademas deberiamos mejorar logica de need_withholding_recompute porque al guardar se está pisando como que requiere recomputo
    # @api.onchange('to_pay_amount', 'withholdable_advanced_amount', 'partner_id', 'regimen_ganancias_id', 'retencion_ganancias', 'date')
    # def _onchange_to_pay_amount(self):
    #     # para muchas retenciones es necesario que el partner este seteado, solo calculamos si viene definido
    #     for rec in self.filtered('partner_id'):
    #         # el compute_withholdings o el _compute_withholdings?
    #         rec._compute_withholdings()
    #         # rec.force_amount_company_currency += rec.payment_difference
    #         # rec.unreconciled_amount = rec.to_pay_amount - rec.selected_debt

    # ver mensaje en commit
    # @api.onchange('retencion_ganancias', 'regimen_ganancias_id')
    # def _onchange_ganancias(self):
    #     # si cambian parametros de ganancias recomputamos retenciones tmb
    #     self._onchange_to_pay_amount()

    @api.depends('company_id.regimenes_ganancias_ids')
    def _company_regimenes_ganancias(self):
        """
        Lo hacemos con campo computado y no related para que solo se setee
        y se exija si es pago de o a proveedor
        """
        for rec in self:
            if rec.partner_type == 'supplier' and not rec.is_internal_transfer:
                rec.company_regimenes_ganancias_ids = rec.company_id.regimenes_ganancias_ids
            else:
                rec.company_regimenes_ganancias_ids = rec.env['afip.tabla_ganancias.alicuotasymontos']

    @api.onchange('commercial_partner_id')
    def change_retencion_ganancias(self):
        # si es exento en ganancias o no tiene clasificacion pero es monotributista, del exterior o consumidor final, sugerimos regimen no_aplica
        if self.partner_id.commercial_partner_id.imp_ganancias_padron in ['EX', 'NC'] or (
            not self.partner_id.commercial_partner_id.imp_ganancias_padron and
            self.partner_id.commercial_partner_id.l10n_ar_afip_responsibility_type_id.code in ('5', '6', '9', '13')):
            self.retencion_ganancias = 'no_aplica'
            self.regimen_ganancias_id = False
        else:
            cia_regs = self.company_regimenes_ganancias_ids
            partner_regimen = (
                self.partner_id.commercial_partner_id.default_regimen_ganancias_id)
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
        if self.partner_id.commercial_partner_id.imp_ganancias_padron in ['EX', 'NC'] or (
            not self.partner_id.commercial_partner_id.imp_ganancias_padron and
            self.partner_id.commercial_partner_id.l10n_ar_afip_responsibility_type_id.code in ('5', '6', '9', '13')):
            self.retencion_ganancias = 'no_aplica'
            self.regimen_ganancias_id = False
        elif self.company_regimenes_ganancias_ids:
            self.retencion_ganancias = 'nro_regimen'

    def _get_name_receipt_report(self, report_xml_id):
        # TODO tal vez mover este reporte y este metodo a l10n_ar_withholding_ux?
        self.ensure_one()
        if self.company_id.country_id.code == 'AR' and self.is_internal_transfer:
            return 'l10n_ar_ux.report_account_transfer'
        return super()._get_name_receipt_report(report_xml_id)
