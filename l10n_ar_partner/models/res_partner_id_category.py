from odoo import api, models, fields
from odoo.osv import expression


class ResPartnerIdCategory(models.Model):
    _inherit = "res.partner.id_category"
    _rec_name = "code"
    _order = "sequence"

    sequence = fields.Integer(
        default=10,
        required=True,
    )
    afip_code = fields.Integer(
        'AFIP Code',
        required=True
    )

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = [
                '|',
                ('code', '=ilike', name + '%'),
                ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        accounts = self.search(domain + args, limit=limit)
        return accounts.name_get()
