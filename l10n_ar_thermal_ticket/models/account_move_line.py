# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _thermal_line_prices(self):
        """Take the prices from the localization helper, as the A4 invoice does.

        The native report calls `_l10n_ar_prices_and_taxes()` on every line of
        every Argentinian invoice, with no condition on the document: the
        helper reads `_l10n_ar_include_vat()` and nothing else. Calling it the
        same way here is what keeps the ticket and the A4 invoice of one
        document from disagreeing, auxiliary documents included.
        """
        self.ensure_one()
        ar_prices = self._l10n_ar_prices_and_taxes()
        return {
            "price_unit": ar_prices["price_unit"],
            "amount": ar_prices["price_subtotal"],
            "discount": self.discount,
        }
