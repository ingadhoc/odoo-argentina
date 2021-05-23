##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    l10n_ar_document_type_ids = fields.Many2many('l10n_latam.document.type', string='Document Types')

    def _get_l10n_ar_afip_pos_types_selection(self):
        """ Add more options to the selection field AFIP POS System, re order options by common use """
        res = super()._get_l10n_ar_afip_pos_types_selection()
        res.append(('not_applicable', _('Not Applicable')),)
        return res

    @api.constrains('l10n_ar_afip_pos_number')
    def _check_afip_pos_number(self):
        return super(AccountJournal, self.filtered(lambda x: x.l10n_ar_afip_pos_system != 'not_applicable'))._check_afip_pos_number()
