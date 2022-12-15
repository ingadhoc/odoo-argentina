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
        account_types = [
            'asset_non_current',
            'asset_fixed',
            'income',
            'income_other',
            'expense',
            'expense_depreciation',
            'equity',
            'expense_direct_cost',
        ]
        accounts = self.search([('account_type', 'in', account_types), ('company_id', 'in', company.ids)])
        if accounts:
            accounts.write({'tag_ids': [(4, non_monetary_tag.id)]})
