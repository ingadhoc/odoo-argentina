##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("reversed_entry_id")
    def _compute_invoice_currency_rate(self):
        super()._compute_invoice_currency_rate()
        ar_reversed_other_currency = self.filtered(
            lambda x: x.is_invoice()
            and x.reversed_entry_id
            and x.company_id.country_id == self.env.ref("base.ar")
            and x.currency_id != x.company_id.currency_id
            and x.reversed_entry_id.currency_id == x.currency_id
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
            lambda x: x.state == "posted"
            and x.invoice_filter_type_domain == "sale"
            and x.l10n_ar_afip_auth_mode == "CAE"
            and x.l10n_ar_afip_auth_code
        ):
            raise UserError(
                _("You cannot cancel documents already posted in AFIP (%s).", ",".join(posted_in_afip.mapped("name")))
            )
        return super().button_cancel()

    def _post(self, soft=True):
        ar_invoices = self.filtered(
            lambda x: x.company_id.account_fiscal_country_id.code == "AR" and x.currency_id != x.company_currency_id
        )
        ar_invoice_line_ids = ar_invoices.mapped("invoice_line_ids").ids

        for line in ar_invoices.mapped("line_ids").filtered(
            lambda x: (x.tax_line_id or x.id in ar_invoice_line_ids)
            and x.currency_rate
            and not x.currency_id.is_zero(abs(x.amount_currency) / x.currency_rate - abs(x.balance))
        ):
            balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)
            line.balance = balance
        res = super()._post(soft=soft)
        return res
