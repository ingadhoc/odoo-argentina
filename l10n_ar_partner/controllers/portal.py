##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal

CustomerPortal.OPTIONAL_BILLING_FIELDS += [
    'main_id_number', 'main_id_category_id']


class L10nArCustomerPortal(CustomerPortal):

    @route()
    def account(self, redirect=None, **post):
        response = super(L10nArCustomerPortal, self).account(
            redirect=redirect, **post)
        document_categories = request.env[
            'res.partner.id_category'].sudo().search([])
        response.qcontext.update({'document_categories': document_categories})
        return response
