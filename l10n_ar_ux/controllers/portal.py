##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal


class L10nArCustomerPortal(CustomerPortal):

    OPTIONAL_BILLING_FIELDS = CustomerPortal.OPTIONAL_BILLING_FIELDS + [
        "commercial_partner_id", "l10n_latam_identification_type_id", "vat",
        "l10n_ar_afip_responsibility_type_id",
    ]

    def details_form_validate(self, data):
        """ When adding either document_type or document_number, this two should be setted """
        error, error_message = super().details_form_validate(data)

        vat = data.get('vat')
        identification_type = data.get('l10n_latam_identification_type_id')
        if identification_type and not vat:
            error['vat'] = 'error'
            error_message.append(_('Please add the document number.'))
        if vat and not identification_type:
            error['l10n_latam_identification_type_id'] = 'error'
            error_message.append(_('Please add the type of document.'))
        write_error, write_message = request.env['res.partner'].try_write_commercial(data)
        if write_error:
            error.update(write_error)
            error_message.extend(write_message)
        return error, error_message

    @route()
    def account(self, redirect=None, **post):
        if post:
            error, _error_message = self.details_form_validate(post)
            if not error:
                post.pop('commercial_partner_id', False)
                post.pop('vat', False)
                post.pop('l10n_latam_identification_type_id', False)
                post.pop('l10n_ar_afip_responsibility_type_id', False)

        response = super().account(redirect=redirect, **post)
        identification_types = request.env['l10n_latam.identification.type'].sudo().search([])
        afip_responsibilities = request.env['l10n_ar.afip.responsibility.type'].sudo().search([])
        uid = request.session.uid
        partner = request.env['res.users'].browse(uid).partner_id if uid else request.env['res.partner']
        partner = partner.with_context(show_address=1).sudo()
        response.qcontext.update({
            'identification_types': identification_types,
            'afip_responsibilities': afip_responsibilities,
            'partner': partner})
        return response
