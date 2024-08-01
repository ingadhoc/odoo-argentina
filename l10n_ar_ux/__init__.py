##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import controllers
from . import models
from odoo import api
from . import wizards
from .hooks import post_init_hook

from odoo.addons.l10n_ar.models.account_fiscal_position import AccountFiscalPosition


def monkey_patches():

    # monkey patch
    @api.model
    def _get_fiscal_position(self, partner, delivery=None):
        if self.env.company.country_id.code == "AR":
            self = self.with_context(
                company_code='AR',
                l10n_ar_afip_responsibility_type_id=partner.l10n_ar_afip_responsibility_type_id.id)
        return super(AccountFiscalPosition, self)._get_fiscal_position(partner, delivery=delivery)

    AccountFiscalPosition._get_fiscal_position = _get_fiscal_position
