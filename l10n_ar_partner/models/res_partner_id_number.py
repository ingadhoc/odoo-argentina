from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class ResPartnerIdNumber(models.Model):

    _inherit = "res.partner.id_number"
    _order = "sequence"

    sequence = fields.Integer(
        default=10,
        required=True,
    )

    @api.constrains('name', 'category_id')
    def check(self):
        if not safe_eval(self.env['ir.config_parameter'].sudo().get_param(
                "l10n_ar_partner.unique_id_numbers", 'False')):
            return True
        for rec in self:
            # we allow same number in related partners
            related_partners = rec.partner_id.search([
                '|', ('id', 'parent_of', rec.partner_id.id),
                ('id', 'child_of', rec.partner_id.id)])
            same_id_numbers = rec.search([
                ('name', '=', rec.name),
                ('category_id', '=', rec.category_id.id),
                # por ahora no queremos la condicion de igual cia
                # ('company_id', '=', rec.company_id.id),
                ('partner_id', 'not in', related_partners.ids),
                # ('id', '!=', rec.id),
            ]) - rec
            if same_id_numbers:
                raise ValidationError(_(
                    'Id Number must be unique per id category!\nSame number '
                    'is only allowed for partner with parent/child relation'))
