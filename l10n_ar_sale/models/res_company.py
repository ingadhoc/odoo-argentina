# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class res_company(models.Model):
    _inherit = "res.company"

    sale_allow_vat_no_discrimination = fields.Selection(
        [('no_discriminate_default', 'Yes, No Discriminate Default'),
         ('discriminate_default', 'Yes, Discrimnate Default')],
        'Sale Allow VAT no discrimination?',
        help="Definie behaviour on sales orders and quoatations reports. "
        "Discrimination or not will depend in partner and company "
        "responsability and AFIP letters setup:"
        "\n* If False, then VAT will be discriminated like always in odoo"
        "\n* If No Discriminate Default, if no match found it won't "
        "discriminate by default"
        "\n* If Discriminate Default, if no match found it would discriminate "
        "by default")
