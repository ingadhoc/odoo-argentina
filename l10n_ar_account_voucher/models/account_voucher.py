# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class account_voucher(models.Model):

    _inherit = "account.voucher"

    document_number = fields.Char(
        string=_('Document Number'),
        related='move_id.document_number',
        readonly=True,
        store=True,
        )
    # agregamos este campo para hacer mas facil la migracion
    afip_document_number = fields.Char(
        string=_('Document Number'),
        related='move_id.afip_document_number',
        readonly=True,
        store=True,
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
    # TODO depreciate this field on v9
    # be care that sipreco project use it
    force_number = fields.Char(
        'Force Number',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False)
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

    _sql_constraints = [
        ('name_uniq', 'unique(document_number, receiptbook_id)',
            'Document number must be unique per receiptbook!')]

    @api.onchange('company_id')
    def _change_company(self):
        self.receiptbook_id = self._get_receiptbook()

    @api.multi
    def _get_receiptbook(self):
        self.ensure_one()
        receiptbook = self.env[
            'account.voucher.receiptbook'].search([
                ('type', '=', self._context.get(
                    'type', self._context.get('default_type', False))),
                ('company_id', '=', self.company_id.id),
                ], limit=1)
        return receiptbook

    @api.multi
    def proforma_voucher(self):
        res = super(account_voucher, self).proforma_voucher()
        sequences = self.env['ir.sequence']
        for voucher in self:
            if not self.receiptbook_id:
                continue
            if voucher.force_number:
                document_number = voucher.force_number
            elif voucher.receiptbook_id.sequence_type == 'automatic':
                document_number = sequences.next_by_id(
                    voucher.receiptbook_id.sequence_id.id)
            elif voucher.receiptbook_id.sequence_type == 'manual':
                document_number = voucher.manual_prefix + (
                    '%%0%sd' % voucher.receiptbook_id.padding % voucher.manual_sufix)
            voucher.move_id.write({
                'afip_document_number': document_number,
                'document_class_id': self.receiptbook_id.document_class_id.id
            })
        return res

    @api.one
    @api.constrains('receiptbook_id', 'company_id')
    def _check_company_id(self):
        """
        Check receiptbook_id and voucher company
        """
        if (self.receiptbook_id and
                self.receiptbook_id.company_id != self.company_id):
            raise Warning(_('The company of the receiptbook and of the \
                voucher must be the same!'))
