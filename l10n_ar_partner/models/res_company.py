# -*- coding: utf-8 -*-
from openerp import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    main_id_category_id = fields.Many2one(
        related='partner_id.main_id_category_id',
    )
    main_id_number = fields.Char(
        related='partner_id.main_id_number',
    )
    cuit = fields.Char(
        related='partner_id.cuit'
    )

    @api.onchange('main_id_category_id')
    def change_main_id_category(self):
        # we force change on partner to get updated number
        self.partner_id.main_id_category_id = self.main_id_category_id
        self.main_id_number = self.partner_id.main_id_number
