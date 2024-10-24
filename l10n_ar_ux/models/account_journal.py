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
<<<<<<< HEAD
||||||| parent of d3ba72ae (temp)
    l10n_latam_manual_checks = fields.Boolean(
        compute="_compute_l10n_latam_manual_checks", store=True, readonly=False,
        inverse='_inverse_l10n_latam_manual_checks', copy=False)

    @api.model
    def _get_checkbooks_by_default_country_codes(self):
        """ Return the list of country codes for the countries where using checkbooks is enable by default """
        return ["AR"]

    @api.depends('outbound_payment_method_line_ids', 'company_id', 'check_manual_sequencing')
    def _compute_l10n_latam_manual_checks(self):
        arg_checks = self.filtered(
                lambda x: not x.check_manual_sequencing and x.company_id.country_id.code in self._get_checkbooks_by_default_country_codes() and
                'check_printing' in x.outbound_payment_method_line_ids.mapped('code'))
        arg_checks.l10n_latam_manual_checks = True
        # disable checkbook if manual sequencing was enable
        self.filtered('check_manual_sequencing').l10n_latam_manual_checks = False

    @api.onchange('l10n_latam_manual_checks')
    def _inverse_l10n_latam_manual_checks(self):
        self.filtered('l10n_latam_manual_checks').check_manual_sequencing = False

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
=======
    l10n_latam_manual_checks = fields.Boolean(
        compute="_compute_l10n_latam_manual_checks", store=True, readonly=False,
        inverse='_inverse_l10n_latam_manual_checks', copy=False)

    @api.model
    def _get_checkbooks_by_default_country_codes(self):
        """ Return the list of country codes for the countries where using checkbooks is enable by default """
        return ["AR"]

    @api.depends('outbound_payment_method_line_ids', 'company_id', 'check_manual_sequencing')
    def _compute_l10n_latam_manual_checks(self):
        arg_checks = self.filtered(
                lambda x: not x.check_manual_sequencing and x.company_id.country_id.code in self._get_checkbooks_by_default_country_codes() and
                'check_printing' in x.outbound_payment_method_line_ids.mapped('code'))
        arg_checks.l10n_latam_manual_checks = True
        # disable checkbook if manual sequencing was enable
        self.filtered('check_manual_sequencing').l10n_latam_manual_checks = False

    @api.onchange('l10n_latam_manual_checks')
    def _inverse_l10n_latam_manual_checks(self):
        self.filtered('l10n_latam_manual_checks').check_manual_sequencing = False

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

    def _get_l10n_ar_afip_pos_types_selection(self):
        """ Add new AFIP Pos type """
        res = super()._get_l10n_ar_afip_pos_types_selection()
        res.append(('CF', _('External Fiscal Controller')))
        return res

    def _get_codes_per_journal_type(self, afip_pos_system):
        """ Add filter for External Fiscal Controller
        NOTE: This can be removed in version 18.0 since has been already included in Odoo """
        tique_codes = ['81', '82', '83', '110', '112', '113', '115', '116', '118', '119', '120']
        if afip_pos_system == 'CF':
            return tique_codes
        res = super()._get_codes_per_journal_type(afip_pos_system)
        for to_remove in ['80', '83']:
            if to_remove in res:
                res.remove(to_remove)
        return res
>>>>>>> d3ba72ae (temp)
