# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models
from openerp.addons.account_document.models.res_company import ResCompany

localizations = ResCompany._localization_selection
new_selection = localizations.append(('argentina', 'Argentina'))
ResCompany._localization_selection = new_selection


class ResCompany(models.Model):
    _inherit = "res.company"

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
