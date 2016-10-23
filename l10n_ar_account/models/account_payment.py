# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # document_number = fields.Char(
    #     string=_('Document Number'),
    #     related='move_id.document_number',
    #     readonly=True,
    #     store=True,
    #     )
    manual_prefix = fields.Char(
        related='receiptbook_id.manual_prefix',
        string='Prefix',
        readonly=True,
        copy=False
    )
    manual_sufix = fields.Integer(
        'Number',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False
    )
    # TODO depreciate this field on v9
    # be care that sipreco project use it
    force_number = fields.Char(
        'Force Number',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False
    )
    receiptbook_id = fields.Many2one(
        'account.voucher.receiptbook',
        'ReceiptBook',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    next_receipt_number = fields.Integer(
        related='receiptbook_id.sequence_id.number_next_actual',
        string='Next Receipt Number',
        readonly=True
    )
    receiptbook_sequence_type = fields.Selection(
        related='receiptbook_id.sequence_type',
        string='Receiptbook Sequence Type',
        readonly=True
    )
    use_argentinian_localization = fields.Boolean(
        related='company_id.use_argentinian_localization',
        string='Use Argentinian Localization?',
        readonly=True,
    )
