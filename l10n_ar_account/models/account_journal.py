# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _
from openerp.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def _get_point_of_sale_types(self):
        return [
            ('manual', 'Manual'),
            ('preprinted', 'Preprinted'),
            ('online', 'Online'),
            # Agregados por otro modulo
            # ('electronic', 'Electronic'),
            # ('fiscal_printer', 'Fiscal Printer'),
            ]

    _point_of_sale_types_selection = (
        lambda self, *args, **kwargs: self._get_point_of_sale_types(
            *args, **kwargs))

    point_of_sale_type = fields.Selection(
        _point_of_sale_types_selection,
        'Point Of Sale Type',
        default='manual',
        required=True,
        )
    point_of_sale_number = fields.Integer(
        'Point Of Sale Number',
        help='On Argentina Localization with use documents and sales journals '
        ' is mandatory'
        )

    _sql_constraints = [(
        'point_of_sale_number_unique',
        'unique(point_of_sale_number, company_id, type)',
        'Point Of Sale Number must be unique per Company!')]

    @api.onchange(
        'type', 'localization', 'use_documents', 'point_of_sale_number',
        'point_of_sale_type', 'sequence_id')
    def change_to_set_name_and_code(self):
        """
        We only set name and code if not sequence_id
        """
        if (
                self.type == 'sale' and
                self.localization == 'argentina' and
                self.use_documents and
                not self.sequence_id
                ):
            (self.name, self.code) = self.get_name_and_code(
                self.point_of_sale_type, self.point_of_sale_number)

    @api.model
    def get_name_and_code(self, point_of_sale_type, point_of_sale_number):
        if point_of_sale_type == 'manual':
            name = 'Manual'
        elif point_of_sale_type == 'preprinted':
            name = 'Preimpresa'
        elif point_of_sale_type == 'online':
            name = 'Online'
        elif point_of_sale_type == 'electronic':
            name = 'Electronica'
        name = '%s %s %04d' % (
            'Ventas', name, point_of_sale_number)
        code = 'V%04d' % (point_of_sale_number)
        return (name, code)

    @api.multi
    def get_journal_letter(self, counterpart_partner=False):
        """Function to be inherited by others"""
        self.ensure_one()
        responsible = self.company_id.afip_responsible_type_id
        if self.type == 'sale':
            resp_field = 'issuer_ids'
        elif self.type == 'purchase':
            resp_field = 'receptor_ids'
        else:
            raise UserError('Letters not implemented for journal type %s' % (
                self.type))
        letters = self.env['account.document.letter'].search([
            '|', (resp_field, 'in', responsible.id),
            (resp_field, '=', False)])

        if counterpart_partner:
            counterpart_resp = counterpart_partner.afip_responsible_type_id
            if self.type == 'sale':
                letters = letters.filtered(
                    lambda x: not x.receptor_ids or
                    counterpart_resp in x.receptor_ids)
            else:
                letters = letters.filtered(
                    lambda x: not x.issuer_ids or
                    counterpart_resp in x.issuer_ids)
        return letters

    @api.multi
    def _update_journal_document_types(self):
        """
        It creates, for journal of type:
            * sale: documents of internal types 'invoice', 'debit_note',
                'credit_note' if there is a match for document letter
        TODO complete here
        """
        self.ensure_one()
        if self.localization != 'argentina':
            return super(
                AccountJournal, self)._update_journal_document_types()

        if not self.use_documents:
            return True

        letters = self.get_journal_letter()

        other_purchase_internal_types = ['in_document', 'ticket']

        if self.type in ['purchase', 'sale']:
            internal_types = ['invoice', 'debit_note', 'credit_note']
            # for purchase we add other documents with letter
            if self.type == 'purchase':
                internal_types += other_purchase_internal_types
        else:
            raise UserError(_('Type %s not implemented yet' % self.type))

        document_types = self.env['account.document.type'].search([
            ('internal_type', 'in', internal_types),
            '|', ('document_letter_id', 'in', letters.ids),
            ('document_letter_id', '=', False)])

        # for purchases we add in_documents and ticket whitout letters
        # TODO ver que no hace falta agregar los tickets aca porque ahora le
        # pusimos al tique generico la letra x entonces ya se agrega solo.
        # o tal vez, en vez de usar letra x, lo deberiamos motrar tambien como
        # factible por no tener letra y ser tique
        if self.type == 'purchase':
            document_types += self.env['account.document.type'].search([
                ('internal_type', 'in', other_purchase_internal_types),
                ('document_letter_id', '=', False)])

        # take out documents that already exists
        document_types = document_types - self.mapped(
            'journal_document_type_ids.document_type_id')

        sequence = 10
        for document_type in document_types:
            sequence_id = False
            if self.type == 'sale':
                # Si es nota de debito nota de credito y same sequence,
                # no creamos la secuencia, buscamos una que exista
                if (
                        document_type.internal_type in [
                        'debit_note', 'credit_note'] and
                        self.document_sequence_type == 'same_sequence'
                        ):
                    journal_document = self.journal_document_type_ids.search([
                        ('document_type_id.document_letter_id', '=',
                            document_type.document_letter_id.id),
                        ('journal_id', '=', self.id)], limit=1)
                    sequence_id = journal_document.sequence_id.id
                else:
                    sequence_id = self.env['ir.sequence'].create(
                        document_type.get_document_sequence_vals(self)).id
            self.journal_document_type_ids.create({
                'document_type_id': document_type.id,
                'sequence_id': sequence_id,
                'journal_id': self.id,
                'sequence': sequence,
            })
            sequence += 10
