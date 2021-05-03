##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    computed_currency_rate = fields.Float(
        compute='_compute_currency_rate',
        string='Currency Rate (preview)',
        digits=(16, 6),
    )

    @api.depends('currency_id', 'company_id', 'invoice_date')
    def _compute_currency_rate(self):
        for rec in self:
            if rec.currency_id and rec.company_id and (rec.currency_id != rec.company_id.currency_id):
                rec.computed_currency_rate = rec.currency_id._convert(
                    1.0, rec.company_id.currency_id, rec.company_id,
                    date=rec.invoice_date or fields.Date.context_today(rec),
                    round=False)
            else:
                rec.computed_currency_rate = 1.0

    @api.model
    def _l10n_ar_get_document_number_parts(self, document_number, document_type_code):
        """
        For compatibility with old invoices/documents we replicate part of previous method
        https://github.com/ingadhoc/odoo-argentina/blob/12.0/l10n_ar_account/models/account_invoice.py#L234
        """
        try:
            return super()._l10n_ar_get_document_number_parts(document_number, document_type_code)
        except Exception:
            _logger.info('Error while getting document number parts, try with backward compatibility')
        invoice_number = point_of_sale = False
        if document_type_code in ['33', '99', '331', '332']:
            point_of_sale = '0'
            # leave only numbers and convert to integer
            # otherwise use date as a number
            if re.search(r'\d', document_number):
                invoice_number = document_number
        elif "-" in document_number:
            splited_number = document_number.split('-')
            invoice_number = splited_number.pop()
            point_of_sale = splited_number.pop()
        elif "-" not in document_number and len(document_number) == 12:
            point_of_sale = document_number[:4]
            invoice_number = document_number[-8:]
        invoice_number = invoice_number and re.sub("[^0-9]", "", invoice_number)
        point_of_sale = point_of_sale and re.sub("[^0-9]", "", point_of_sale)
        if not invoice_number or not point_of_sale:
            raise ValidationError(_(
                'No pudimos obtener el número de factura y de punto de venta para %s %s. Verifique que tiene un número '
                'cargado similar a "00001-00000001"') % (document_type_code, document_number))
        return {
                'invoice_number': int(invoice_number),
                'point_of_sale': int(point_of_sale),
            }

    # TODO this is only for compatibility with old versions, remove this method when go live to 14/15 version
    @api.constrains('name', 'partner_id', 'company_id')
    def _check_unique_vendor_number(self):
        """ We overwrite original method odoo/odoo/l10n_latam_invoice_document in order to be able to search for
        document numbers that has POS of 4 or 5 digits. In 13.0 we will always have 5 digits, but we need this for
        compatibility of old version migrated clients that have used 4 digits POS numbers """
        ar_purchase_use_document = self.filtered(
            lambda x: x.company_id.country_id.code == 'AR' and x.is_purchase_document() and x.l10n_latam_use_documents
            and x.l10n_latam_document_number and x.l10n_latam_document_type_id.code)

        super(AccountMove, self - ar_purchase_use_document)._check_unique_vendor_number()
        for rec in ar_purchase_use_document:
            # Old 4 digits name
            number = rec._l10n_ar_get_document_number_parts(
                rec.l10n_latam_document_number, rec.l10n_latam_document_type_id.code)
            old_name_compat = "%s %04d-%08d" % (
                rec.l10n_latam_document_type_id.doc_code_prefix, number['point_of_sale'], number['invoice_number'])

            domain = [
                ('type', '=', rec.type),
                # by validating name we validate l10n_latam_document_number and l10n_latam_document_type_id
                '|', ('name', '=', old_name_compat), ('name', '=', rec.name),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
                ('commercial_partner_id', '=', rec.commercial_partner_id.id)
            ]
            if rec.search(domain):
                raise ValidationError(_('Vendor bill number must be unique per vendor and company.'))

    @api.constrains('ref', 'type', 'partner_id', 'journal_id', 'invoice_date')
    def _check_duplicate_supplier_reference(self):
        """ We make reference only unique if you are not using documents.
        Documents already guarantee to not encode twice same vendor bill """
        return super(
            AccountMove, self.filtered(lambda x: not x.l10n_latam_use_documents))._check_duplicate_supplier_reference()

    def _get_name_invoice_report(self, report_xml_id):
        """Use always argentinian like report (regardless use documents)"""
        self.ensure_one()
        if self.company_id.country_id.code == 'AR':
            custom_report = {
                'account.report_invoice_document_with_payments': 'l10n_ar.report_invoice_document_with_payments',
                'account.report_invoice_document': 'l10n_ar.report_invoice_document',
            }
            return custom_report.get(report_xml_id) or report_xml_id
        return super()._get_name_invoice_report(report_xml_id)
