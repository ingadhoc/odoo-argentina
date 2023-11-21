##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    qr_code_label = fields.Char(
        string="QR Code Label",
        help="String to display before the QR Code on the invoice report."
    )
    qr_code = fields.Char(
        string="QR Code",
        help="String to generate the QR Code that will be displayed on the invoice report."
    )
    discriminate_taxes = fields.Selection(
        [
            ('yes', 'Yes'),
            ('no', 'No'),
            ('according_to_partner', 'According to partner VAT responsibility')
        ],
        string='Discriminate taxes?',
        default='no',
        required=True,
    )
    l10n_ar_afip_pos_partner_id = fields.Many2one(string='Dirección Punto de venta')
