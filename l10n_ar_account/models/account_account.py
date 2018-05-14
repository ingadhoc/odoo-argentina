# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class AccountAccount(models.Model):

    _inherit = 'account.account'

    afip_activity_id = fields.Many2one(
        'afip.activity',
        'AFIP Activity',
        help='AFIP activity, used for IVA f2002 report',
        auto_join=True,
    )
    vat_f2002_category_id = fields.Many2one(
        'afip.vat.f2002_category',
        auto_join=True,
        string='Categoría IVA f2002',
    )
