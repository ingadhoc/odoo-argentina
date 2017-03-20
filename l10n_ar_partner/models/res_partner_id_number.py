# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import UserError
from openerp.tools.safe_eval import safe_eval


class ResPartnerIdNumber(models.Model):
    _inherit = "res.partner.id_number"
    _order = "sequence"

    sequence = fields.Integer(
        default=10,
        required=True,
    )

    @api.multi
    @api.constrains('name', 'category_id')
    def check(self):
        if not safe_eval(self.env['ir.config_parameter'].get_param(
                "l10n_ar_partner.unique_id_numbers", 'False')):
            return True
        for rec in self:
            if rec.search([
                    ('name', '=', rec.name),
                    ('category_id', '=', rec.category_id.id),
                    ('id', '!=', rec.id)]):
                raise UserError(_(
                    'Id Number must be unique per id category'))
