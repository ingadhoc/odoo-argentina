# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _get_localizations(self):
        localizations = super(ResCompany, self)._get_localizations()
        localizations.append(['argentina', 'Argentina'])
        return localizations

    gross_income_number = fields.Char(
        related='partner_id.gross_income_number',
        string='Gross Income'
    )
    gross_income_type = fields.Selection(
        related='partner_id.gross_income_type',
        string='Gross Income'
    )
    start_date = fields.Date(
        related='partner_id.start_date',
    )
    afip_responsability_type_id = fields.Many2one(
        related='partner_id.afip_responsability_type_id',
    )
    # TODO ver si lo movemos a account_document
    # journal_ids = fields.One2many(
    #     'account.journal',
    #     'company_id',
    #     'Journals'
    #     )
