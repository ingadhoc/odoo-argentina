# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields
import logging
_logger = logging.getLogger(__name__)


class account_voucher_receiptbook(models.Model):

    _name = 'account.voucher.receiptbook'
    _description = 'Account Voucher Receiptbook'
    _order = 'sequence asc'

    def init(self, cr):
        """
        Esto es para instalar si teniamos account_voucher_receipt y antes de
        desinstalar este ultimo para no perder algunos datos
        """
        _logger.info(
            "Update data ids to 'l10n_ar_account_voucher'")

        data_ids = [
            'sequence_customer_receipt_1',
            'sequence_supplier_receipt_1',
            'customer_receiptbook_1',
            'supplier_receiptbook_1',
            'customer_receiptbook_2',
            'supplier_receiptbook_2',
            ]

        cr.execute(
            """UPDATE ir_model_data set module='l10n_ar_account_voucher' where
            module='account_voucher_receipt' and name in %s""" % (
                str(tuple(data_ids))))

        _logger.info(
            "Updating fields external id for receiptbook "
            "so you can uninstall this module'")
        field_prefix = 'field_account_voucher_receiptbook_'
        fields_sufixs = [
            'sequence', 'name', 'type', 'sequence_type', 'sequence_id',
            'company_id', 'manual_prefix', 'padding', 'active',
            'document_class_id']
        fields_with_prefix = []
        for field in fields_sufixs:
            fields_with_prefix.append("%s%s" % (field_prefix, field))

        _logger.info("Moving fields of account_voucher_receipt' if installed")

        cr.execute(
            """UPDATE ir_model_data set module='l10n_ar_account_voucher' where
            module='account_voucher_receipt' and name in %s""" % (
                str(tuple(fields_with_prefix))))

    sequence = fields.Integer(
        'Sequence',
        help="Used to order the receiptbooks"
        )
    name = fields.Char(
        'Name',
        size=64,
        readonly=False,
        required=True,
        )
    type = fields.Selection(
        [('receipt', 'Receipt'), ('payment', 'Payment')],
        string='Type',
        readonly=False,
        required=True,
        )
    sequence_type = fields.Selection(
        [('automatic', 'Automatic'), ('manual', 'Manual')],
        string='Sequence Type',
        readonly=False,
        required=True,
        default='automatic',
        )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Entry Sequence',
        help="This field contains the information related to the numbering\
        of the receipt entries of this receiptbook.",
        required=False,
        default=10,
        copy=False,
        )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env[
            'res.company']._company_default_get('account.voucher.receiptbook')
        )
    manual_prefix = fields.Char(
        'Prefix',
        )
    padding = fields.Integer(
        'Number Padding',
        help="automatically adds some '0' on the left of the 'Number' to get\
        the required padding size."
        )
    active = fields.Boolean(
        'Active',
        default=True,
        )
    document_class_id = fields.Many2one(
        'afip.document_class',
        'Document Class',
        required=True,
        )
