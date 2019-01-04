##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api
from odoo.addons.account_document.models.res_company import ResCompany


class ResCompany(models.Model):
    _inherit = "res.company"

    localization = fields.Selection(
        selection_add=[('argentina', 'Argentina')],
    )
    gross_income_number = fields.Char(
        related='partner_id.gross_income_number',
        string='Gross Income'
    )
    gross_income_type = fields.Selection(
        related='partner_id.gross_income_type',
        string='Gross Income'
    )
    gross_income_jurisdiction_ids = fields.Many2many(
        related='partner_id.gross_income_jurisdiction_ids',
    )
    start_date = fields.Date(
        related='partner_id.start_date',
    )
    afip_responsability_type_id = fields.Many2one(
        related='partner_id.afip_responsability_type_id',
    )
    company_requires_vat = fields.Boolean(
        related='afip_responsability_type_id.company_requires_vat',
        readonly=True,
    )
    # use globally as default so that if child companies are created they
    # also use this as default
    tax_calculation_rounding_method = fields.Selection(
        default='round_globally',
    )
    arba_cit = fields.Char(
        'CIT ARBA',
        help='Clave de Identificación Tributaria de ARBA',
    )

    @api.onchange('localization')
    def change_localization(self):
        if self.localization == 'argentina' and not self.country_id:
            self.country_id = self.env.ref('base.ar')
    # TODO ver si lo movemos a account_document
    # journal_ids = fields.One2many(
    #     'account.journal',
    #     'company_id',
    #     'Journals'
    #     )
