# -*- coding: utf-8 -*-
from openerp import fields, models


class account_voucher_receiptbook(models.Model):

    _name = 'account.voucher.receiptbook'
    _description = 'Account Voucher Receiptbook'
    _order = 'sequence asc'

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
        defualt=True,
        )
    document_class_id = fields.Many2one(
        'afip.document_class',
        'Document Class',
        required=True,
        )
