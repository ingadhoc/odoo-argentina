##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import re

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_round


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("reversed_entry_id")
    def _compute_invoice_currency_rate(self):
        super()._compute_invoice_currency_rate()
        ar_reversed_other_currency = self.filtered(
            lambda x: (
                x.is_invoice()
                and x.reversed_entry_id
                and x.company_id.country_id == self.env.ref("base.ar")
                and x.currency_id != x.company_id.currency_id
                and x.reversed_entry_id.currency_id == x.currency_id
            )
        )
        for rec in ar_reversed_other_currency:
            rec.invoice_currency_rate = rec.reversed_entry_id.invoice_currency_rate

    def _get_name_invoice_report(self):
        """Use always argentinian like report (regardless use documents)"""
        self.ensure_one()
        if self.company_id.country_id.code == "AR":
            return "l10n_ar.report_invoice_document"
        return super()._get_name_invoice_report()

    def _l10n_ar_include_vat(self):
        self.ensure_one()
        if not self.l10n_latam_use_documents:
            discriminate_taxes = self.journal_id.discriminate_taxes
            if discriminate_taxes == "yes":
                return False
            elif discriminate_taxes == "no":
                return True
            else:
                return not (
                    self.company_id.l10n_ar_company_requires_vat
                    and self.partner_id.l10n_ar_afip_responsibility_type_id.code in ["1"]
                    or False
                )
        return self.l10n_latam_document_type_id.l10n_ar_letter in ["B", "C", "X", "R"]

    @api.model
    def _l10n_ar_get_document_number_parts(self, document_number, document_type_code):
        # eliminamos todo lo que viene después '(' que es un sufijo que odoo agrega y que nosotros agregamos para
        # forzar unicidad con cambios de approach al ir migrando de versiones
        document_number = document_number.split("(")[0]
        return super()._l10n_ar_get_document_number_parts(document_number, document_type_code)

    def button_cancel(self):
        """
        Evitamos que se pueda cancelar una factura que ya fue previamente confirmada y enviada a AFIP.
        Este caso se da cuando dos usuarios están a la vez editando la misma factura, uno confirma
        y el otro, sin refrescar, cancela.
        """
        if posted_in_afip := self.filtered(
            lambda x: (
                x.state == "posted"
                and x.invoice_filter_type_domain == "sale"
                and x.l10n_ar_afip_auth_mode == "CAE"
                and x.l10n_ar_afip_auth_code
            )
        ):
            raise UserError(
                _("You cannot cancel documents already posted in AFIP (%s).", ",".join(posted_in_afip.mapped("name")))
            )
        return super().button_cancel()

    def _post(self, soft=True):
        # EXTEND account
        """It fixes the rounding on invoice lines to ensure consistency with
        the applied rate (currency is not company currency).This is only applied
        on invoice move types."""
        ar_invoices = self.filtered(
            lambda x: (
                x.company_id.account_fiscal_country_id.code == "AR"
                and x.currency_id != x.company_currency_id
                and x.is_invoice()
            )
        )
        ar_invoice_line_ids = ar_invoices.mapped("invoice_line_ids").ids

        for line in ar_invoices.mapped("line_ids").filtered(
            lambda x: (
                (x.tax_line_id or x.id in ar_invoice_line_ids)
                and x.currency_rate
                and not x.currency_id.is_zero(abs(x.amount_currency) / x.currency_rate - abs(x.balance))
            )
        ):
            balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)
            line.balance = balance
        res = super()._post(soft=soft)
        return res

    def _get_next_sequence_format(self):
        # Always take the POS from the journal: a name with a stale POS must not propagate to new documents
        format_string, format_values = super()._get_next_sequence_format()
        pos_number = self.journal_id.l10n_ar_afip_pos_number
        if (
            self.journal_id.l10n_ar_is_pos
            and pos_number
            and self.l10n_latam_use_documents
            and self.l10n_latam_document_type_id
            and self.company_id.account_fiscal_country_id.code == "AR"
        ):
            format_values["prefix1"] = re.sub(r"\d{5}-$", "%05d-" % pos_number, format_values["prefix1"])
        return format_string, format_values

    @api.model
    def _get_l10n_ar_codes_used_for_inv_and_ref(self):
        return super()._get_l10n_ar_codes_used_for_inv_and_ref() + ["33", "331"]

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if self.journal_id.company_id.account_fiscal_country_id.code == "AR" and self.move_type in [
            "out_refund",
            "in_refund",
        ]:
            # The parent builds: ['|', ('code', 'in', codes)] + ar_domain.
            # In Odoo's prefix notation this parses as (code in codes) OR (first_ar_condition),
            # leaving country_id outside the OR. This lets document types from other LatAm
            # countries that share the same codes (e.g. Chilean doc 33) slip through.
            # AND-ing country_id here ensures only AR document types are returned.
            ar_country_id = self.journal_id.company_id.account_fiscal_country_id.id
            domain = expression.AND([domain, [("country_id", "=", ar_country_id)]])
        return domain

    def _l10n_ar_get_amounts(self, base_lines=None):
        """Posted documents report the non-VAT taxes amounts booked in their tax lines.

        Upstream recomputes them from the current tax definition, so a posted document whose tax was later
        archived or turned into a fixed 0 (e.g. replaced during a migration) reports 0 in the VAT book TXT
        and in the electronic invoice requests, while the ledger still holds the real amount.
        """
        res = super()._l10n_ar_get_amounts(base_lines=base_lines)
        if self.state != "posted":
            return res
        profits_tax_group = (
            self.env["account.chart.template"]
            .with_company(self.company_id)
            .ref("tax_group_percepcion_ganancias", raise_if_not_found=False)
        )
        sign = -1 if self.is_inbound() else 1
        if (
            self.move_type in ("out_refund", "in_refund")
            and self.l10n_latam_document_type_id.code in self._get_l10n_ar_codes_used_for_inv_and_ref()
        ):
            sign = -sign

        def booked(tax_lines):
            return float_round(sign * sum(tax_lines.mapped("amount_currency")), precision_digits=2)

        tax_lines = self.line_ids.filtered("tax_line_id")
        non_vat_lines = tax_lines.filtered(lambda line: not line.tax_line_id.tax_group_id.l10n_ar_vat_afip_code)
        res["not_vat_taxes_amount"] = booked(non_vat_lines)
        for tribute_code, key in (
            ("07", "iibb_perc_amount"),
            ("08", "mun_perc_amount"),
            ("04", "intern_tax_amount"),
            ("99", "other_taxes_amount"),
            ("06", "vat_perc_amount"),
        ):
            res[key] = booked(
                tax_lines.filtered(lambda line: line.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code == tribute_code)
            )
        res["profits_perc_amount"] = booked(
            tax_lines.filtered(lambda line: line.tax_line_id.tax_group_id == profits_tax_group)
        )
        return res
