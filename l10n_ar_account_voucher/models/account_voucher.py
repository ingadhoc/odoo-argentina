# -*- coding: utf-8 -*-
from openerp import models, fields, api


class account_voucher(models.Model):

    _inherit = "account.voucher"

    @api.model
    def _get_receiptbook(self):
        receiptbook_ids = self.env[
            'account.voucher.receiptbook'].search(
            [('type', '=', self._context.get('type', False))])
        return receiptbook_ids and receiptbook_ids[0] or False

    # document_reference = fields.Char(
    #     compute='_get_document_number',
    #     string='Document Number',
    #     readonly=True,
    #     )
    document_number = fields.Char(
        string='Document Number',
        copy=False,
        readonly=True,
        )
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
    force_number = fields.Char(
        'Force Number',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False)
    receiptbook_id = fields.Many2one(
        'account.voucher.receiptbook',
        'ReceiptBook',
        readonly=True,
        required=True,
        states={'draft': [('readonly', False)]},
        default=_get_receiptbook,
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

    _sql_constraints = [
        ('name_uniq', 'unique(document_number, receiptbook_id)',
            'Document number must be unique per receiptbook!')]

    # def post_receipt(self, cr, uid, ids, context=None):
    #     res = super(account_voucher_receipt, self).post_receipt(
    #         cr, uid, ids, context)
    #     for receipt in self.browse(cr, uid, ids, context=context):
    #         for voucher in receipt.voucher_ids:
    #             voucher.move_id.write({
    #                 'afip_document_number': receipt.name,
    #                 'document_class_id': receipt.receiptbook_id.afip_document_class_id and receipt.receiptbook_id.afip_document_class_id.id or False,
    #             })
    #     return res

    # @api.multi
    # def cancel_voucher(self):
    #     ''' Mofication of cancel voucher so it cancels the receipts when
    #     voucher is cancelled'''

    #     res = super(account_voucher, self).cancel_voucher()
    #     for voucher in self:
    #         if voucher.receipt_id and voucher.receipt_id.state != 'draft':
    #             voucher.receipt_id.cancel_receipt()
    #     return res

    # @api.multi
    # def action_cancel_draft(self):
    #     res = super(account_voucher, self).action_cancel_draft()
    #     for voucher in self:
    #         if voucher.receipt_id:
    #             voucher.receipt_id.action_cancel_draft()
    #     return res