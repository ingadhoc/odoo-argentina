##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


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

    @api.model
    def set_no_monetaria_tag(self, company):
        """ Set no monetaria tag to the corresponding accounts taking into
        account the account type
        """
        tag = self.env.ref('l10n_ar_account.no_monetaria_tag')
        xml_ids = [
            'account.data_account_type_non_current_assets',  # Activos
                                                             # no-Corriente
            'account.data_account_type_fixed_assets',  # Activos fijos
            'account.data_account_type_other_income',  # Otros Ingresos
            'account.data_account_type_revenue',  # Ingreso
            'account.data_account_type_expenses',  # Gastos
            'account.data_account_type_depreciation', # Depreciación
            'account.data_account_type_equity', # Capital
            'account.data_account_type_direct_costs',  # Coste de Ingreso
        ]
        account_types = []
        for xml_id in xml_ids:
            account_types.append(self.env.ref(xml_id).id)
        accounts = self.search([
            ('user_type_id', 'in', account_types),
            ('company_id', 'in', company.ids)])
        if accounts:
            accounts.write({'tag_ids': [(4, tag.id)]})
