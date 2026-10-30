##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    gross_income_jurisdiction_ids = fields.Many2many(
        related="partner_id.gross_income_jurisdiction_ids",
        readonly=False,
    )
    # TODO this field could be defined directly on l10n_ar_account_withholding
    arba_cit = fields.Char(
        "CIT ARBA",
        help="ARBA Tax Identification Key. A branch with the same CUIT that leaves it empty uses the one of its "
        "parent company.",
    )
    # la fecha de comienzo de actividades puede ser por cada punto de venta distinta, lo convertimos a related del
    # partner
    l10n_ar_afip_start_date = fields.Date(related="partner_id.start_date", string="Activities Start", readonly=False)
    l10n_ar_report_signature = fields.Image("Firma", copy=False, attachment=True)
    l10n_ar_report_signed_by = fields.Text("Aclaracion", copy=False)
    l10n_ar_invoice_report_ars_amount = fields.Boolean("Mostrar importe equivalente en ARS", default=False)

    def _l10n_ar_get_same_cuit_ancestors(self):
        """``self`` followed by the ancestors that are its same fiscal entity, nearest first.

        Walks up while the parent declares the same CUIT and stops at the first break. The CUIT
        is compared as ``account_ux`` does for ``legal_entity_root_id`` (literal Tax ID, ``/``
        counts as none), so both agree on what the fiscal entity is. A company without CUIT is
        its own fiscal entity and only returns itself.
        """
        self.ensure_one()

        def cuit(company):
            vat = (company.vat or "").strip()
            return "" if vat == "/" else vat

        companies = self
        own_cuit = cuit(self.sudo())
        parent = self.sudo().parent_id
        while own_cuit and parent and cuit(parent) == own_cuit:
            companies |= self.browse(parent.id)
            parent = parent.parent_id
        return companies

    def _l10n_ar_get_same_cuit_company_with(self, field_name):
        """The nearest of ``self`` and its same fiscal entity ancestors with ``field_name`` set,
        in sudo, or an empty recordset.

        Shares credentials (CIT, COT) down the branches of a fiscal entity: a branch only needs
        its own when it differs from the parent's. In sudo because the user may not have access
        to the parent company.
        """
        self.ensure_one()
        return self._l10n_ar_get_same_cuit_ancestors().sudo().filtered(field_name)[:1]

    @api.model
    def _l10n_ar_ux_hide_invoice_tax_company_currency(self):
        """Disable "Taxes in company currency" on Argentinian companies.

        Odoo adds this setting in 18.0 with default True, so every company gets it enabled on install or upgrade
        and the AR legal invoice report prints an extra taxes box in ARS on foreign currency invoices.
        """
        self.search([("account_fiscal_country_id.code", "=", "AR")]).write(
            {"display_invoice_tax_company_currency": False}
        )
