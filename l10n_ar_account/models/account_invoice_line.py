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

    @api.model
    def create(self, vals):
        rec = super(AccountInvoiceLine, self).create(vals)
        rec.check_vat_tax()
        return rec

    @api.multi
    def check_vat_tax(self):
        """For recs of companies with company_requires_vat (that comes from
        the responsability), we ensure one and only one vat tax is configured
        """
        # por ahora, para no romper los tests de odoo y datos demo de algunos
        # modulos, lo desactivamos en la instalacion
        if self.env.registry.in_test_mode():
            return True
        for rec in self.filtered('company_id.company_requires_vat'):
            vat_taxes = rec.invoice_line_tax_ids.filtered(
                lambda x:
                x.tax_group_id.tax == 'vat' and x.tax_group_id.type == 'tax')
            if len(vat_taxes) != 1:
                raise UserError(_(
                    'Debe haber un y solo un impuestos de IVA por línea. '
                    'Verificar líneas con producto "%s"' % (
                        rec.product_id.name)))

    @api.multi
    def write(self, vals):
        res = super(AccountInvoiceLine, self).write(vals)
        # for performance we only check if tax or company is on vals
        if 'invoice_line_tax_ids' in vals or 'company_id' in vals:
            self.check_vat_tax()
        return res
