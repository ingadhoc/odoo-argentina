##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import copy

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.fields import Domain


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
        """Eliminamos todo lo que viene después '(' que es un sufijo que odoo agrega y que nosotros agregamos para
        forzar unicidad con cambios de approach al ir migrando de versiones.
        Captamos con un try/except para no romper en caso de que el formato no sea el esperado. En Odoo no podemos
        replicarlo, por eso lo dejamos acá."""
        try:
            document_number = document_number.split("(")[0]
            return super()._l10n_ar_get_document_number_parts(document_number, document_type_code)
        except ValueError:
            raise UserError(
                _("The associated document number does not appear to be in the Argentine format: %s", document_number)
            )

    def button_cancel(self):
        """
        Evitamos que se pueda cancelar una factura que ya fue previamente confirmada y enviada a ARCA.
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
                _("You cannot cancel documents already posted in ARCA (%s).", ",".join(posted_in_afip.mapped("name")))
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

    @api.model
    def _get_l10n_ar_codes_used_for_inv_and_ref(self):
        return super()._get_l10n_ar_codes_used_for_inv_and_ref() + ["33", "331"]

    # NOTE: the following three methods port odoo/odoo#234040 (merged in Odoo master, not in 19.0).
    # They must be dropped when migrating to a version that already includes it.

    def _l10n_ar_is_refund_invoice(self):
        """Check if the document type is in the list of document types that can be used as an invoice and
        as a refund and the move type is 'in_refund' or 'out_refund'."""
        return (
            self.l10n_latam_document_type_id.code in self._get_l10n_ar_codes_used_for_inv_and_ref()
            and self.move_type in ["in_refund", "out_refund"]
        )

    def _apply_refund_adjustments(self, tax_totals):
        """Adjust tax totals for refund invoices that share the same ARCA codes as the invoice they reverse."""
        for suffix in ("", "_currency"):
            for prefix in ("base", "tax", "total"):
                field = f"{prefix}_amount{suffix}"
                if tax_totals[field]:
                    tax_totals[field] *= -1
            for subtotal in tax_totals["subtotals"]:
                for prefix in ("base", "tax"):
                    field = f"{prefix}_amount{suffix}"
                    if subtotal[field]:
                        subtotal[field] *= -1
                for tax_group in subtotal["tax_groups"]:
                    for prefix in ("display_base", "base", "tax"):
                        field = f"{prefix}_amount{suffix}"
                        if tax_group[field]:
                            tax_group[field] *= -1

    def _l10n_ar_get_invoice_totals_for_report(self):
        """If the invoice document type indicates that vat should not be detailed in the printed report (result of
        _l10n_ar_include_vat()) then we overwrite tax_totals field so that includes taxes in the total amount,
        otherwise it would be showing amount_untaxed in the amount_total.
        Also, if the invoice is a refund and shares the same ARCA code as the invoice it is reversing, we apply
        adjustments to the tax totals to reflect the amounts in negative.

        Full override of l10n_ar (no super call) mirroring odoo/odoo#234040. We deepcopy tax_totals so the
        adjustments do not mutate the computed field cache."""
        self.ensure_one()
        tax_totals = copy.deepcopy(self.tax_totals)
        if self._l10n_ar_is_refund_invoice():
            self._apply_refund_adjustments(tax_totals)
        include_vat = self._l10n_ar_include_vat()
        if not include_vat:
            return tax_totals

        tax_group_ids = {
            tax_group["id"] for subtotal in tax_totals["subtotals"] for tax_group in subtotal["tax_groups"]
        }
        tax_group_ids_to_exclude = (
            self.env["account.tax.group"]
            .browse(tax_group_ids)
            .filtered(
                lambda tax_group: (
                    self._l10n_ar_is_tax_group_other_national_ind_tax(tax_group)
                    or self._l10n_ar_is_tax_group_vat(tax_group)
                    or (
                        self._l10n_ar_is_transparency_document()
                        and self._l10n_ar_is_tax_group_iibb_perception(tax_group)
                    )
                )
            )
            .ids
        )
        if tax_group_ids_to_exclude:
            if self._l10n_ar_is_refund_invoice():
                self._apply_refund_adjustments(tax_totals)
            tax_totals = self.env["account.tax"]._exclude_tax_groups_from_tax_totals_summary(
                tax_totals, tax_group_ids_to_exclude
            )
        return tax_totals

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
            domain = Domain(domain) & Domain([("country_id", "=", ar_country_id)])
        return domain
