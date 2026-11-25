# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_thermal_header_partner(self):
        """Head the receipt with the partner of the ARCA point of sale.

        That partner is the address the fiscal authority ties to the point of
        sale, and it is what the native invoice report prints, so a POS with
        its own address does not print the company one. Journals outside ARCA
        keep the generic behaviour.
        """
        self.ensure_one()
        return self.journal_id.l10n_ar_afip_pos_partner_id or super()._get_thermal_header_partner()

    def _thermal_prices_include_taxes(self):
        """Defer to the localization, which already answers this for any move.

        `_l10n_ar_include_vat()` reads the letter of a fiscal document, and
        `l10n_ar_ux` extends it for documents without one: there the journal
        setting `discriminate_taxes` decides, and when it is left on automatic
        the rule is whether the company charges VAT and the customer is a
        Responsable Inscripto. Spelling a rule of our own here would make the
        ticket and the A4 invoice of the same document disagree.
        """
        self.ensure_one()
        return self._l10n_ar_include_vat()

    def _get_thermal_receipt_report_name(self):
        """Print the fiscal ticket only for invoices issued through ARCA.

        The point of sale number is what ties a journal to the fiscal
        authority: journals without one (typically an auxiliary company that
        does not invoice electronically) have no letter, no CAE and no QR, so
        rendering the fiscal template for them would print those blocks empty.

        They are not left bare for it. The Argentinian blocks that do not
        depend on an authorised document -the identification of both parties,
        the VAT of each line, the breakdown of the totals- reach the generic
        ticket through `report_thermal_invoice_html_ar`, which extends it
        instead of replacing it.
        """
        self.ensure_one()
        if self.journal_id.l10n_ar_afip_pos_number:
            return "l10n_ar_thermal_ticket.report_thermal_invoice_html"
        return super()._get_thermal_receipt_report_name()
