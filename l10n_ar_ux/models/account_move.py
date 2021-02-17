##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
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
