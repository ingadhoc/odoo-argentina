##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


# for performance
# TODO this should be suggested to odoo by a PR
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    invoice_id = fields.Many2one(
        auto_join=True,
    )
