##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class AccountMove(models.Model):
    _inherit = "account.move"

    # Solo para condicionar el aviso en la vista: si el contacto no tiene responsabilidad, no proponemos
    # documentos y hay que ofrecer el link para ir a completarla.
    l10n_ar_ux_partner_responsibility_id = fields.Many2one(
        related="commercial_partner_id.l10n_ar_afip_responsibility_type_id",
        string="ARCA Responsibility",
    )

    l10n_ar_ux_document_number_placeholder = fields.Char(
        compute="_compute_l10n_ar_ux_document_number_placeholder",
    )

    @api.depends("l10n_latam_document_type_id")
    def _compute_l10n_ar_ux_document_number_placeholder(self):
        """El formato del número depende del tipo de documento: los despachos de importación son 16 caracteres
        y el resto va punto de venta y número separados por guión (ver _format_document_number de l10n_ar)."""
        for rec in self:
            document_type = rec.l10n_latam_document_type_id
            placeholder = False
            if document_type.country_id.code == "AR" and document_type.code:
                placeholder = "1234567890123456" if document_type.code in ["66", "67"] else "00001-00000001"
            rec.l10n_ar_ux_document_number_placeholder = placeholder

    def action_l10n_ar_ux_set_partner_responsibility(self):
        """Abre un wizard para definir la responsabilidad del contacto sin salir de la factura: al aceptar se
        guarda en el contacto, se refrescan los tipos de documento de esta factura y volvés al borrador."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Set the ARCA Responsibility"),
            "res_model": "l10n_ar_ux.partner.responsibility",
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id},
        }

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

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        if (
            self.company_id.account_fiscal_country_id.code == "AR"
            and self.l10n_latam_use_documents
            and not self.commercial_partner_id.l10n_ar_afip_responsibility_type_id
        ):
            # Sin la responsabilidad ARCA no sabemos qué letras corresponden: el dominio de l10n_ar deja pasar
            # solo los documentos sin letra (exterior y excepcionales) y se autoselecciona el primero. Preferimos
            # no proponer nada antes que autoseleccionar un Despacho de importación.
            return Domain.FALSE
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
