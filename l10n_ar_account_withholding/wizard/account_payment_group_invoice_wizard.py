from odoo import fields, models


class AccountPaymentGroupInvoiceWizard(models.TransientModel):
    _inherit = "account.payment.group.invoice.wizard"

    afip_asoc_period_start = fields.Date(
        'Associate Period From',
    )

    afip_asoc_period_end = fields.Date(
        'Associate Period To',
    )

    origin = fields.Many2one(
        'account.invoice',
    )

    commercial_partner_id = fields.Many2one(
        'res.partner',
        related="payment_group_id.partner_id.commercial_partner_id"
    )

    def get_invoice_vals(self):
        self.ensure_one()
        invoice_vals = super().get_invoice_vals()
        invoice_vals.update({
            'afip_asoc_period_start': self.afip_asoc_period_start,
            'afip_asoc_period_end': self.afip_asoc_period_end,
            'origin': self.origin
        })
        return invoice_vals
