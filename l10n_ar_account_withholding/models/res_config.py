# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'
    
    regimenes_ganancias_ids = fields.Many2many(related='company_id.regimenes_ganancias_ids')
