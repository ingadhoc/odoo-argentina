##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class L10nArCustomerPortal(CustomerPortal):
    def _is_argentine_company(self):
        return request.env.company.country_code == "AR"

    def _get_optional_fields(self):
        # EXTEND 'portal'
        optional_fields = super()._get_optional_fields()
        ar_fields = [
            "l10n_latam_identification_type_id",
            "l10n_ar_afip_responsibility_type_id",
            "vat",
        ]
        if self._is_argentine_company():
            optional_fields = list(dict.fromkeys(optional_fields + ar_fields))
        return optional_fields

    def _prepare_portal_layout_values(self):
        # EXTEND 'portal'
        portal_layout_values = super()._prepare_portal_layout_values()

        if self._is_argentine_company():
            website_sale_installed = (
                request.env["ir.module.module"]
                .sudo()
                .search([("name", "=", "l10n_ar_website_sale"), ("state", "!=", "uninstalled")])
            )
            partner = request.env.user.partner_id
            portal_layout_values.update(
                {
                    "responsibility": partner.l10n_ar_afip_responsibility_type_id,
                    "partner_sudo": partner,
                    "identification": partner.l10n_latam_identification_type_id,
                    "responsibility_types": request.env["l10n_ar.afip.responsibility.type"].search([]),
                    "identification_types": request.env["l10n_latam.identification.type"].search(
                        ["|", ("country_id", "=", False), ("country_id.code", "=", "AR")]
                    ),
                    "website_sale_installed": True if website_sale_installed else False,
                }
            )

        return portal_layout_values

    def details_form_validate(self, data, partner_creation=False):
        """When adding either document_type or document_number, this two should be setted"""
        error, error_message = super().details_form_validate(data, partner_creation)

        # sanitize identification values to make sure it's correctly written on the partner
        if self._is_argentine_company():
            for identification_field in ("l10n_latam_identification_type_id", "l10n_ar_afip_responsibility_type_id"):
                if data.get(identification_field):
                    data[identification_field] = int(data[identification_field])
        return error, error_message
