##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_ar_prices_and_taxes(self):
        """Port of odoo/odoo#234040 (merged in Odoo master, not in 19.0): show line amounts in negative on
        refunds that share the same ARCA document code as the invoice they reverse.
        Drop when migrating to a version that already includes it."""
        res = super()._l10n_ar_prices_and_taxes()
        if self.move_id._l10n_ar_is_refund_invoice():
            for key in ("price_unit", "price_subtotal", "price_net"):
                if res[key]:
                    res[key] *= -1
        return res
