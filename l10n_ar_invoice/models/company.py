# -*- coding: utf-8 -*-
from openerp import fields, models


class res_company(models.Model):
    _inherit = "res.company"

    use_argentinian_localization = fields.Boolean(
        string="Use Argentinian Localization?",
        default=True)
    responsability_id = fields.Many2one(
        related='partner_id.responsability_id',
        relation='afip.responsability',
        string="Responsability",)
    iibb = fields.Char(
        related='partner_id.iibb',
        string='Gross Income')
    start_date = fields.Date(
        related='partner_id.start_date',
        string='Start-up Date',)
    invoice_vat_discrimination_default = fields.Selection(
        [('no_discriminate_default', 'Yes, No Discriminate Default'),
         ('discriminate_default', 'Yes, Discriminate Default')],
        'Invoice VAT discrimination default',
        default='no_discriminate_default',
        required=True,
        help="Definie behaviour on invoices reports. Discrimination or not will depend in partner and company responsability and AFIP letters setup:\
            * If No Discriminate Default, if no match found it won't discriminate by default\
            * If Discriminate Default, if no match found it would discriminate by default\
            ")
