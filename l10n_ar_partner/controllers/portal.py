##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal


class L10nArCustomerPortal(CustomerPortal):

    OPTIONAL_BILLING_FIELDS = CustomerPortal.OPTIONAL_BILLING_FIELDS + [
        "commercial_partner_id", "main_id_category_id", "main_id_number",
        "afip_responsability_type_id",
    ]

    def details_form_validate(self, data):
        """ When adding either document_type or document_number, this two
        should be setted.
        """
        error, error_message = super(
            L10nArCustomerPortal, self).details_form_validate(data)

        main_id_number = data.get('main_id_number', False)
        main_id_category_id = data.get('main_id_category_id', False)
        if main_id_category_id and not main_id_number:
            error['main_id_number'] = 'error'
            error_message.append(_(
                'Please add the document number.'))
        if main_id_number and not main_id_category_id:
            error['main_id_category_id'] = 'error'
            error_message.append(_(
                'Please add the type of document.'))
        return error, error_message

    @route()
    def account(self, redirect=None, **post):
        post_process = False
        if post:
            error, _error_message = self.details_form_validate(post)
            if not error:
                commercial_partner_id = post.pop(
                    'commercial_partner_id', False)
                if commercial_partner_id:
                    post_process = True
                    commercial_values = dict(
                        main_id_number=post.pop('main_id_number'),
                        main_id_category_id=post.pop('main_id_category_id'),
                        afip_responsability_type_id=post.pop(
                            'afip_responsability_type_id'),
                    )

        response = super(L10nArCustomerPortal, self).account(
            redirect=redirect, **post)
        document_categories = request.env[
            'res.partner.id_category'].sudo().search([])
        afip_responsabilities = request.env[
            'afip.responsability.type'].sudo().search([])
        uid = request.session.uid
        partner = request.env['res.users'].browse(uid).partner_id if uid else \
            request.env['res.partner']
        partner = partner.with_context(show_address=1).sudo()
        response.qcontext.update({
            'document_categories': document_categories,
            'afip_responsabilities': afip_responsabilities,
            'partner': partner,
            })

        if post_process:
            partner.commercial_partner_id.write(commercial_values)

        return response
