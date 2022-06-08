##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    l10n_ar_document_type_ids = fields.Many2many('l10n_latam.document.type', string='Document Types')
    qr_code_label = fields.Char(
        string="QR Code Label",
        help="String to display before the QR Code on the invoice report."
    )
    qr_code = fields.Char(
        string="QR Code",
        help="String to generate the QR Code that will be displayed on the invoice report."
    )
    l10n_ar_is_pos = fields.Boolean(compute="_compute_l10n_ar_is_pos", store=True, readonly=False, string="Is AFIP POS?")
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

    @api.onchange('l10n_ar_is_pos')
    def _onchange_l10n_ar_is_pos(self):
        # TODO on v15 move to standar and maybe make l10n_ar_afip_pos_system computed stored
        if not self.l10n_ar_is_pos:
            self.l10n_ar_afip_pos_system = False

    @api.depends('country_code', 'type', 'l10n_latam_use_documents')
    def _compute_l10n_ar_is_pos(self):
        ar_sale_use_documents = self.filtered(
            lambda x: x.country_code == 'AR' and x.type == 'sale' and x.l10n_latam_use_documents)
        ar_sale_use_documents.l10n_ar_is_pos = True
        (self - ar_sale_use_documents).l10n_ar_is_pos = False

    @api.constrains('l10n_ar_afip_pos_number')
    def _check_afip_pos_number(self):
        to_review = self.filtered(lambda x: x.l10n_ar_is_pos)
        super(AccountJournal, to_review)._check_afip_pos_number()

    def use_specific_document_types(self):
        self.ensure_one()
        return self.l10n_latam_use_documents and (
            (self.type == 'sale' and not self.l10n_ar_is_pos) or
            (self.type == 'purchase' and self.l10n_ar_is_pos))

    def _l10n_ar_journal_issuer_is_supplier(self):
        self.ensure_one()
        return self.l10n_latam_use_documents and (
            (self.type == 'sale' and not self.l10n_ar_is_pos) or
            (self.type == 'purchase' and self.l10n_ar_is_pos))
