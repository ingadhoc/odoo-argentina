##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request, route


class L10nArCustomerPortal(CustomerPortal):
    # OPTIONAL_BILLING_FIELDS = CustomerPortal.OPTIONAL_BILLING_FIELDS + [
    #     "commercial_partner_id", "l10n_latam_identification_type_id", "vat",
    #     "l10n_ar_afip_responsibility_type_id",
    # ]

    def details_form_validate(self, data, partner_creation=False):
        """When adding either document_type or document_number, this two should be setted"""
        error, error_message = super().details_form_validate(data, partner_creation=partner_creation)

        vat = data.get("vat")
        identification_type = data.get("l10n_latam_identification_type_id")
        if identification_type and not vat:
            error["vat"] = "error"
            error_message.append(_("Please add the document number."))
        if vat and not identification_type:
            error["l10n_latam_identification_type_id"] = "error"
            error_message.append(_("Please add the type of document."))
        write_error, write_message = request.env["res.partner"].try_write_commercial(data)
        if write_error:
            error.update(write_error)
            error_message.extend(write_message)
        return error, error_message

    def values_preprocess_ar(self, values):
        """We preprocess the ar-post data to ensure the correct assignment of many2one fields."""
        new_values = dict()
        partner_fields = request.env["res.partner"]._fields
        ar_camp = ["l10n_ar_afip_responsibility_type_id", "l10n_latam_identification_type_id", "commercial_partner_id"]

        for k, v in values.items():
            # Convert the values for many2one fields to integer since they are used as IDs
            if k in partner_fields and k in ar_camp and partner_fields[k].type == "many2one":
                new_values[k] = bool(v) and int(v) or False

        return new_values

    @route()
    def account(self, redirect=None, **post):
        partner = request.env.user.partner_id
        if post and request.httprequest.method == "POST":
            if not partner.can_edit_vat():
                post["country_id"] = str(partner.country_id.id)
            error, _error_message = self.details_form_validate(post)
            # Procesamos los datos del post para asignar correctamente los valores de los campos many2one
            post.update(self.values_preprocess_ar(post))

        response = super().account(redirect=redirect, **post)
        identification_types = request.env["l10n_latam.identification.type"].sudo().search([])
        afip_responsibilities = request.env["l10n_ar.afip.responsibility.type"].sudo().search([])
        uid = request.session.uid
        partner = request.env["res.users"].browse(uid).partner_id if uid else request.env["res.partner"]
        partner = partner.with_context(show_address=1).sudo()
        response.qcontext.update(
            {
                "afip_respo_type": post.get("l10n_ar_afip_responsibility_type_id")
                or partner.l10n_ar_afip_responsibility_type_id.id,
                "latam_ident_type": post.get("l10n_latam_identification_type_id")
                or partner.l10n_latam_identification_type_id.id,
                "identification_types": identification_types,
                "afip_responsibilities": afip_responsibilities,
                "partner": partner,
                "partner_can_edit_vat": partner.can_edit_vat(),
            }
        )
        return response
