##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import controllers
from . import models
from . import reports
from . import wizards
from .hooks import post_init_hook

from odoo.addons.l10n_latam_invoice_document.models.account_move import AccountMove
from odoo.exceptions import UserError


def monkey_patch_inverse_l10n_latam_document_number():
    # monkey patch
    orginal_method = AccountMove._inverse_l10n_latam_document_number

    def _inverse_l10n_latam_document_number(self):
        """ Parche feo para poder usar liquidaciones hasta que se mezcle https://github.com/odoo/odoo/pull/78632 en
        master"""
        orginal_method(self)
        to_review = self.filtered(lambda x: (
            x.journal_id.l10n_ar_is_pos
            and x.l10n_latam_document_type_id
            and x.l10n_latam_document_number
            and (x.l10n_latam_manual_document_number or not x.highest_name)
        ))
        for rec in to_review:
            number = rec.l10n_latam_document_type_id._format_document_number(rec.l10n_latam_document_number)
            current_pos = int(number.split("-")[0])
            if current_pos != rec.journal_id.l10n_ar_afip_pos_number:
                invoices = self.search([('journal_id', '=', rec.journal_id.id), ('posted_before', '=', True)], limit=1)
                # If there is no posted before invoices the user can change the POS number (x.l10n_latam_document_number)
                if (not invoices):
                    rec.journal_id.l10n_ar_afip_pos_number = current_pos
                    rec.journal_id._onchange_set_short_name()
                # If not, avoid that the user change the POS number
                else:
                    raise UserError(_('The document number can not be changed for this journal, you can only modify'
                                      ' the POS number if there is not posted (or posted before) invoices'))

    AccountMove._inverse_l10n_latam_document_number = _inverse_l10n_latam_document_number
