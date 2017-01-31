# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _
from openerp.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    gross_income_number = fields.Char(
        'Gross Income Number',
        size=64,
    )
    gross_income_type = fields.Selection([
        ('multilateral', 'Multilateral'),
        ('local', 'Local'),
        ('no_liquida', 'No Liquida'),
    ],
        'Gross Income Type',
    )
    gross_income_jurisdiction_ids = fields.Many2many(
        'res.country.state',
        string='Gross Income Jurisdictions',
        help='The state of the company is cosidered the main jurisdiction'
    )
    start_date = fields.Date(
        'Start-up Date'
    )
    afip_responsability_type_id = fields.Many2one(
        'afip.responsability.type',
        'AFIP Responsability Type',
    )

    @api.multi
    @api.constrains('gross_income_jurisdiction_ids', 'state_id')
    def check_gross_income_jurisdictions(self):
        for rec in self:
            if rec.state_id and \
                    rec.state_id in rec.gross_income_jurisdiction_ids:
                raise UserError(_(
                    'Jurisdiction %s is considered the main jurisdiction '
                    'because it is the state of the company, please remove it'
                    'from the jurisdiction list') % rec.state_id.name)
