# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
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
    gross_income_number = fields.Char(
        related='partner_id.gross_income_number',
        string='Gross Income')
    # for compatibility
    iibb = fields.Char(
        related='gross_income_number'
        )
    gross_income_type = fields.Selection(
        related='partner_id.gross_income_type',
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
    point_of_sale_ids = fields.One2many(
        'afip.point_of_sale',
        'company_id',
        'AFIP Point of Sales',
        )
    journal_ids = fields.One2many(
        'account.journal',
        'company_id',
        'Journals'
        )
