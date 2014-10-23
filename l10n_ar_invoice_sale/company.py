# -*- coding: utf-8 -*-
from openerp import fields, models


class res_company(models.Model):
    _inherit = "res.company"
    sale_allow_vat_no_discrimination = fields.Selection(
        [('no_discriminate_default', 'Yes, No Discriminate Default'),
         ('discriminate_default', 'Yes, Discrimnate Default')],
        'Sale Allow VAT no discrimination?',
        help="Definie behaviour on sales orders and quoatations reports. Discrimination or not will depend in partner and company responsability and AFIP letters setup:\
            * If False, then VAT will be discriminated like always in odoo\
            * If No Discriminate Default, if no match found it won't discriminate by default\
            * If Discriminate Default, if no match found it would discriminate by default\
            ")
