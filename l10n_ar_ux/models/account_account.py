##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class AccountAccount(models.Model):

    _inherit = 'account.account'

    @api.model
    def set_non_monetary_tag(self, company):
        """ Set <Non Monetary> tag to the corresponding accounts taking into account the account type """
        non_monetary_tag = self.env.ref('l10n_ar_ux.no_monetaria_tag')
        xml_ids = [
            'account.data_account_type_non_current_assets',
            'account.data_account_type_fixed_assets',
            'account.data_account_type_other_income',
            'account.data_account_type_revenue',
            'account.data_account_type_expenses',
            'account.data_account_type_depreciation',
            'account.data_account_type_equity',
            'account.data_account_type_direct_costs',
        ]
        account_types = [self.env.ref(xml_id).id for xml_id in xml_ids]
        accounts = self.search([('user_type_id', 'in', account_types), ('company_id', 'in', company.ids)])
        if accounts:
            accounts.write({'tag_ids': [(4, non_monetary_tag.id)]})
