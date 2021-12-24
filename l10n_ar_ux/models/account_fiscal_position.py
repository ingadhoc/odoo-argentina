# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.addons.l10n_ar.models.account_fiscal_position import AccountFiscalPosition


@api.model
def get_fiscal_position(self, partner_id, delivery_id=None):
    company = self.env.company
    if company.country_id.code == "AR":
        partner = self.env['res.partner'].browse(partner_id)
        self = self.with_context(l10n_ar_afip_responsibility_type_id=partner.l10n_ar_afip_responsibility_type_id.id)
    return super(AccountFiscalPosition, self).get_fiscal_position(partner_id, delivery_id=delivery_id)


AccountFiscalPosition.get_fiscal_position = get_fiscal_position


class AccountFiscalPositionMp(models.Model):

    _inherit = 'account.fiscal.position'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Take into account the partner afip responsibility in order to auto-detect the fiscal position """
        if 'l10n_ar_afip_responsibility_type_id' in self._context:
            args += [
                '|',
                ('l10n_ar_afip_responsibility_type_ids', '=', False),
                ('l10n_ar_afip_responsibility_type_ids', '=', self._context.get('l10n_ar_afip_responsibility_type_id'))]
        return super()._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)

    def _onchange_afip_responsibility(self):
        return {}
