##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.l10n_ar.models.account_move import AccountMove
from odoo.addons.l10n_latam_invoice_document.models.account_move import AccountMove as AccountMoveOriginal
import re
import logging
_logger = logging.getLogger(__name__)


def _inverse_l10n_latam_document_number(self):
    """ Parche feo para poder usar liquidaciones hasta que se mezcle https://github.com/odoo/odoo/pull/78632 en
    master"""
    AccountMoveOriginal._inverse_l10n_latam_document_number(self)
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


class AccountMove(models.Model):
    _inherit = "account.move"

    computed_currency_rate = fields.Float(
        compute='_compute_currency_rate',
        string='Currency Rate (preview)',
        digits=(16, 6),
    )
    l10n_ar_currency_rate = fields.Float(compute='_compute_l10n_ar_currency_rate', store=True)

    @api.depends('reversed_entry_id')
    def _compute_l10n_ar_currency_rate(self):
        """ If it's a credit note on foreign currency and foreing currency is the same as original credit note, then
        we use original invoice rate """
        ar_reversed_other_currency = self.filtered(
            lambda x: x.is_invoice() and x.reversed_entry_id and
            x.company_id.country_id == self.env.ref('base.ar') and
            x.currency_id != x.company_id.currency_id and
            x.reversed_entry_id.currency_id == x.currency_id)
        self.filtered(lambda x: x.move_type == 'entry').l10n_ar_currency_rate = False
        for rec in ar_reversed_other_currency:
            rec.l10n_ar_currency_rate = rec.reversed_entry_id.l10n_ar_currency_rate

    @api.depends('currency_id', 'company_id', 'date', 'invoice_date')
    def _compute_currency_rate(self):
        need_currency_rate = self.filtered(lambda x: x.currency_id and x.company_id and (x.currency_id != x.company_id.currency_id))
        remaining = self - need_currency_rate
        for rec in need_currency_rate:
            if rec.l10n_ar_currency_rate:
                rec.computed_currency_rate = rec.l10n_ar_currency_rate
            else:
                rec.computed_currency_rate = rec.currency_id._convert(
                    1.0, rec.company_id.currency_id, rec.company_id,
                    # para previsualizar lo que sería la tasa usamos la fecha contable, sino usamos la fecha al día de hoy
                    # la fecha contable en facturas de venta realmente está seteada cuando el invoice_date está activo o
                    # posterior a la validación de la factura es por eso que comparamos invoice_date
                    date=rec.date if rec.invoice_date else fields.Date.context_today(rec),
                    round=False)
        remaining.computed_currency_rate = 1.0

    @api.constrains('ref', 'move_type', 'partner_id', 'journal_id', 'invoice_date')
    def _check_duplicate_supplier_reference(self):
        """ We make reference only unique if you are not using documents.
        Documents already guarantee to not encode twice same vendor bill """
        return super(
            AccountMove, self.filtered(lambda x: not x.l10n_latam_use_documents))._check_duplicate_supplier_reference()

    def _get_name_invoice_report(self):
        """Use always argentinian like report (regardless use documents)"""
        self.ensure_one()
        if self.company_id.country_id.code == 'AR':
            return 'l10n_ar.report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        # TODO: add prefix "_l10n_ar" to method use_specific_document_types
        if self.company_id.country_id == self.env.ref('base.ar') and self.journal_id.use_specific_document_types():
            return [
                ('id', 'in', self.journal_id.l10n_ar_document_type_ids.ids),
                '|', ('code', 'in', self._get_l10n_ar_codes_used_for_inv_and_ref()),
                ('internal_type', 'in', ['credit_note'] if self.move_type in ['out_refund', 'in_refund'] else ['invoice', 'debit_note']),
            ]
        return super()._get_l10n_latam_documents_domain()

    def _post(self, soft=True):
        """ recompute debit/credit sending force_rate on context """
        other_curr_ar_invoices = self.filtered(
            lambda x: x.is_invoice() and
            x.company_id.country_id == self.env.ref('base.ar') and x.currency_id != x.company_id.currency_id)
        # llamamos a todos los casos de otra moneda y no solo a los que tienen "l10n_ar_currency_rate" porque odoo
        # tiene una suerte de bug donde solo recomputa los debitos/creditos en ciertas condiciones, pero puede
        # ser que esas condiciones no se cumplan y la cotizacion haya cambiado (por ejemplo la factura tiene fecha y
        # luego se cambia la cotizacion, al validar no se recomputa). Si odoo recomputase en todos los casos seria
        # solo necesario iterar los elementos con l10n_ar_currency_rate y hacer solo el llamado a super
        for rec in other_curr_ar_invoices:
            # si no tiene fecha en realidad en llamando a super ya se recomputa con el llamado a _onchange_invoice_date
            # también se recomputa con algo de lock dates llamando a _onchange_invoice_date, pero por si no se dan
            # esas condiciones o si odoo las cambia, llamamos al onchange_currency por las dudas
            rec.with_context(
                check_move_validity=False, force_rate=rec.l10n_ar_currency_rate)._onchange_currency()

            # tambien tenemos que pasar force_rate aca por las dudas de que super entre en onchange_currency en los
            # mismos casos mencionados recien
            res = super(AccountMove, rec.with_context(force_rate=rec.l10n_ar_currency_rate))._post(soft=soft)
        res = super(AccountMove, self - other_curr_ar_invoices)._post(soft=soft)
        return res

    def _l10n_ar_include_vat(self):
        self.ensure_one()
        if not self.l10n_latam_use_documents:
            discriminate_taxes = self.journal_id.discriminate_taxes
            if discriminate_taxes == 'yes':
                return False
            elif discriminate_taxes == 'no':
                return True
            else:
                return not (
                    self.company_id.l10n_ar_company_requires_vat and
                    self.partner_id.l10n_ar_afip_responsibility_type_id.code in ['1'] or False)
        return self.l10n_latam_document_type_id.l10n_ar_letter in ['B', 'C', 'X', 'R']

    def _is_manual_document_number(self):
        res = super()._is_manual_document_number()
        # when issuer is supplier de numbering works opposite (supplier numerate invoices, customer encode bill)
        if self.country_code == 'AR' and self.journal_id._l10n_ar_journal_issuer_is_supplier():
            return not res
        return res
