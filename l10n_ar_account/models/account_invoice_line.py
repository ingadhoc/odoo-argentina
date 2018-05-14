##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    vat_tax_id = fields.Many2one(
        'account.tax',
        # field to help with electronic invoice and perhups in other uses
        compute='_compute_vat_tax_id',
    )

    @api.multi
    @api.depends(
        'invoice_line_tax_ids.tax_group_id.type',
        'invoice_line_tax_ids.tax_group_id.tax',
    )
    def _compute_vat_tax_id(self):
        for rec in self:
            vat_tax_id = rec.invoice_line_tax_ids.filtered(lambda x: (
                x.tax_group_id.type == 'tax' and
                x.tax_group_id.tax == 'vat'))
            if len(vat_tax_id) > 1:
                raise UserError(_('Only one vat tax allowed per line'))
            rec.vat_tax_id = vat_tax_id
