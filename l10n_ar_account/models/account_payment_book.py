# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class account_voucher_receiptbook(models.Model):

    _name = 'account.voucher.receiptbook'
    _description = 'Account Voucher Receiptbook'
    _order = 'sequence asc'

    sequence = fields.Integer(
        'Sequence',
        help="Used to order the receiptbooks",
        default=10,
    )
    name = fields.Char(
        'Name',
        size=64,
        required=True,
    )
    type = fields.Selection(
        [('receipt', 'Receipt'), ('payment', 'Payment')],
        string='Type',
        required=True,
    )
    sequence_type = fields.Selection(
        [('automatic', 'Automatic'), ('manual', 'Manual')],
        string='Sequence Type',
        readonly=False,
        default='automatic',
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Entry Sequence',
        help="This field contains the information related to the numbering "
        "of the receipt entries of this receiptbook.",
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
        required=True,
        # TODO rename field to prefix
    )
    padding = fields.Integer(
        'Number Padding',
        help="automatically adds some '0' on the left of the 'Number' to get "
        "the required padding size."
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

    @api.model
    def create(self, vals):
        sequence_type = vals.get(
            'sequence_type',
            self._context.get('default_sequence_type', False))
        voucher_type = vals.get(
            'type',
            self._context.get('default_type', False))
        manual_prefix = vals.get(
            'manual_prefix',
            self._context.get('default_manual_prefix', False))
        company_id = vals.get(
            'company_id',
            self._context.get('default_company_id', False))

        if (
                sequence_type == 'automatic' and
                not vals.get('sequence_id', False) and
                company_id and voucher_type):
            seq_vals = {
                'name': vals['name'],
                'implementation': 'no_gap',
                'prefix': manual_prefix,
                'padding': 8,
                'number_increment': 1
            }
            sequence = self.env['ir.sequence'].sudo().create(seq_vals)
            vals.update({
                'sequence_id': sequence.id
            })
        return super(account_voucher_receiptbook, self).create(vals)
