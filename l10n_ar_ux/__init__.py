##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import controllers
from . import models
from odoo import api
from . import reports
from . import wizards
from .hooks import post_init_hook

from odoo.addons.l10n_ar.models.account_fiscal_position import AccountFiscalPosition
from odoo.addons.account.models.account_move_line import AccountMoveLine


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

    # monkey patch
    @api.depends('currency_id', 'company_id', 'move_id.date')
    def _compute_currency_rate(self):
        print("---- MONKEY _compute_currency_rate")
        def get_rate(from_currency, to_currency, company, date):
            res = self.env['res.currency']._get_conversion_rate(
                from_currency=from_currency,
                to_currency=to_currency,
                company=company,
                date=date,
            )
            return res
        for line in self:
            if line.currency_id:
                line.currency_rate = get_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line),
                )
            else:
                line.currency_rate = 1

    AccountMoveLine._compute_currency_rate = _compute_currency_rate
