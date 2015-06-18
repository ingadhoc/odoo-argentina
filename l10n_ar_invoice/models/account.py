# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning


class account_fiscal_position(models.Model):
    _inherit = 'account.fiscal.position'

    afip_code = fields.Char('AFIP Code')


class afip_tax_code(models.Model):
    _inherit = 'account.tax.code'

    afip_code = fields.Integer('AFIP Code')
    type = fields.Selection([
        ('tax', 'TAX'),
        ('perception', 'Perception'),
        ('withholding', 'Withholding'),
        ('other', 'Other')],
        )
    tax = fields.Selection([
        ('vat', 'VAT'),
        ('profits', 'Profits'),
        ('gross_income', 'Gross Income'),
        ('other', 'Other')],
        )
    application = fields.Selection([
        ('national_taxes', 'National Taxes'),
        ('provincial_taxes', 'Provincial Taxes'),
        ('municipal_taxes', 'Municipal Taxes'),
        ('internal_taxes', 'Internal Taxes'),
        ('others', 'Others')],
        help='Other Taxes According AFIP',
        )
    application_code = fields.Char(
        'Application Code',
        compute='get_application_code',
        )

    @api.one
    @api.depends('application')
    def get_application_code(self):
        if self.application == 'national_taxes':
            application_code = '01'
        elif self.application == 'provincial_taxes':
            application_code = '02'
        elif self.application == 'municipal_taxes':
            application_code = '03'
        elif self.application == 'internal_taxes':
            application_code = '04'
        else:
            application_code = '99'
        self.application_code = application_code


class account_move(models.Model):
    _inherit = "account.move"

    document_class_id = fields.Many2one(
        'afip.document_class',
        'Document Type',
        copy=False,
        # readonly=True
        )
    afip_document_number = fields.Char(
        string='Document Number',
        copy=False,
        )

    @api.one
    @api.depends(
        'afip_document_number',
        'name',
        'document_class_id',
        # we disable this depnd because it makes update module performance low
        # 'document_class_id.doc_code_prefix',
    )
    def _get_document_number(self):
        if self.afip_document_number and self.document_class_id:
            document_number = (
                self.document_class_id.doc_code_prefix or '') + \
                self.afip_document_number
        else:
            document_number = self.name
        self.document_number = document_number

    document_number = fields.Char(
        compute='_get_document_number',
        string='Document Number',
        readonly=True,
        store=True
    )


class account_move_line(models.Model):
    _inherit = "account.move.line"

    @api.one
    def name_get(self):
        if self.ref:
            name = ((self.id, (self.document_number or '')+' ('+self.ref+')'))
        else:
            name = ((self.id, self.document_number))
        return name

    document_class_id = fields.Many2one(
        'afip.document_class',
        'Document Type',
        related='move_id.document_class_id',
        store=True,
        readonly=True,
    )
    document_number = fields.Char(
        string='Document Number',
        related='move_id.document_number',
        store=True,
        readonly=True,
    )


class account_journal_afip_document_class(models.Model):
    _name = "account.journal.afip_document_class"
    _description = "Journal Afip Documents"
    _rec_name = 'afip_document_class_id'
    _order = 'journal_id desc, sequence, id'

    afip_document_class_id = fields.Many2one(
        'afip.document_class',
        'Document Type',
        required=True
        )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Entry Sequence',
        required=False,
        help="This field contains the information related to the numbering of the documents entries of this document type."
        )
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        required=True
        )
    sequence = fields.Integer(
        'Sequence',
        )


class account_journal(models.Model):
    _inherit = "account.journal"

    journal_document_class_ids = fields.One2many(
        'account.journal.afip_document_class',
        'journal_id',
        'Documents Class',
        )
    point_of_sale_id = fields.Many2one(
        'afip.point_of_sale', 'Point of sale'
        )
    point_of_sale = fields.Integer(
        related='point_of_sale_id.number',
        string='Point of sale',
        readonly=True
        )
    use_documents = fields.Boolean(
        'Use Documents?'
        )
    document_sequence_type = fields.Selection(
        [('own_sequence', 'Own Sequence'),
            ('same_sequence', 'Same Invoice Sequence')],
        string='Document Sequence Type',
        help="Use own sequence or invoice sequence on Debit and Credit Notes?"
        )

    @api.one
    @api.constrains(
        'point_of_sale_id',
        'company_id',
        'use_documents',
        )
    def check_document_classes(self):
        """
        Tricky constraint to create documents on journal
        """
        if not self.use_documents:
            return True

        responsability = self.company_id.responsability_id
        if self.type in ['sale', 'sale_refund']:
            letter_ids = [x.id for x in responsability.issued_letter_ids]
        elif self.type in ['purchase', 'purchase_refund']:
            letter_ids = [x.id for x in responsability.received_letter_ids]

        if self.type in ['purchase', 'sale']:
            document_types = ['invoice', 'debit_note']
        elif self.type in ['purchase_refund', 'sale_refund']:
            document_types = ['credit_note']

        document_classes = self.env['afip.document_class'].search(
            [('document_letter_id', 'in', letter_ids),
             ('document_type', 'in', document_types)])

        created_document_class_ids = [
            x.afip_document_class_id.id for x in self.journal_document_class_ids]

        sequence = 10
        for document_class in document_classes:
            sequence_id = False
            if document_class.id in created_document_class_ids:
                continue
            if self.type in ['sale', 'sale_refund']:
                # Si es nota de debito nota de credito y same sequence, no creamos la secuencia, buscamos una que exista
                if document_class.document_type in [
                        'debit_note', 'credit_note'] and self.document_sequence_type == 'same_sequence':
                    journal_documents = self.journal_document_class_ids.search(
                        [('afip_document_class_id.document_letter_id', '=', document_class.document_letter_id.id),
                         ('journal_id.point_of_sale', '=', self.point_of_sale)])
                    sequence_id = journal_documents and journal_documents[0].sequence_id.id or False
                else:
                    sequence_id = self.env['ir.sequence'].create({
                        'name': self.name + ' - ' + document_class.name,
                        'padding': 8,
                        'prefix': "%04i-" % (self.point_of_sale),
                        'company_id': self.company_id.id,
                    }).id
            self.journal_document_class_ids.create({
                'afip_document_class_id': document_class.id,
                'sequence_id': sequence_id,
                'journal_id': self.id,
                'sequence': sequence,
            })
            sequence += 10

    @api.one
    @api.constrains('point_of_sale_id', 'company_id')
    def _check_company_id(self):
        """
        Check point of sale and journal company
        """
        if self.point_of_sale_id and self.point_of_sale_id.company_id != self.company_id:
            raise Warning(_('The company of the point of sale and of the \
                journal must be the same!'))


class res_currency(models.Model):
    _inherit = "res.currency"
    afip_code = fields.Char(
        'AFIP Code', size=4
        )
