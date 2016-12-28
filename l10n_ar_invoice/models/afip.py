# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class afip_incoterm(models.Model):
    _name = 'afip.incoterm'
    _description = 'Afip Incoterm'

    afip_code = fields.Char(
        'Code', required=True)
    name = fields.Char(
        'Name', required=True)


class afip_point_of_sale(models.Model):
    _name = 'afip.point_of_sale'
    _description = 'Afip Point Of Sale'

    prefix = fields.Char(
        'Prefix'
        )
    sufix = fields.Char(
        'Sufix'
        )
    type = fields.Selection([
        ('manual', 'Manual'),
        ('preprinted', 'Preprinted'),
        ('online', 'Online'),
        # Agregados por otro modulo
        # lo agregamos para facilitar migracion
        ('electronic', 'Electronic'),
        # ('fiscal_printer', 'Fiscal Printer'),
        ],
        'Type',
        default='manual',
        required=True,
        )
    name = fields.Char(
        compute='get_name',
        )
    number = fields.Integer(
        'Number', required=True
        )
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'afip.point_of_sale')
        )
    journal_ids = fields.One2many(
        'account.journal',
        'point_of_sale_id',
        'Journals',
        )
    document_sequence_type = fields.Selection(
        [('own_sequence', 'Own Sequence'),
            ('same_sequence', 'Same Invoice Sequence')],
        string='Document Sequence Type',
        default='own_sequence',
        required=True,
        help="Use own sequence or invoice sequence on Debit and Credit Notes?"
        )
    journal_document_class_ids = fields.One2many(
        'account.journal.afip_document_class',
        compute='get_journal_document_class_ids',
        string=_('Documents Classes'),
        )

    @api.one
    @api.depends('type', 'sufix', 'prefix', 'number')
    def get_name(self):
        # TODO mejorar esto y que tome el lable traducido del selection
        if self.type == 'manual':
            name = 'Manual'
        elif self.type == 'preprinted':
            name = 'Preimpresa'
        elif self.type == 'online':
            name = 'Online'
        elif self.type == 'electronic':
            name = 'Electronica'
        if self.prefix:
            name = '%s %s' % (self.prefix, name)
        if self.sufix:
            name = '%s %s' % (name, self.sufix)
        name = '%04d - %s' % (self.number, name)
        self.name = name

    @api.one
    @api.depends('journal_ids.journal_document_class_ids')
    def get_journal_document_class_ids(self):
        journal_document_class_ids = self.env[
            'account.journal.afip_document_class'].search([
                ('journal_id.point_of_sale_id', '=', self.id)])
        self.journal_document_class_ids = journal_document_class_ids

    _sql_constraints = [('number_unique', 'unique(number, company_id)',
                         'Number Must be Unique per Company!'), ]


class afip_document_class(models.Model):
    _name = 'afip.document_class'
    _description = 'Afip Document Class'

    name = fields.Char(
        'Name', size=120)
    doc_code_prefix = fields.Char(
        'Document Code Prefix', help="Prefix for Documents Codes on Invoices \
        and Account Moves. For eg. 'FA ' will build 'FA 0001-0000001' Document Number")
    afip_code = fields.Integer(
        'AFIP Code')
    document_letter_id = fields.Many2one(
        'afip.document_letter', 'Document Letter')
    report_name = fields.Char(
        'Name on Reports',
        help='Name that will be printed in reports, for example "CREDIT NOTE"')
    document_type = fields.Selection([
        ('invoice', 'Invoices'),
        ('debit_note', 'Debit Notes'),
        ('credit_note', 'Credit Notes'),
        ('ticket', 'Ticket'),
        ('receipt_invoice', 'Receipt Invoice'),
        ('in_document', 'In Document'),
        ],
        string='Document Type',
        help='It defines some behaviours on different places:\
        * invoice: used on sale and purchase journals. Auto selected if not\
        debit_note specified on context.\
        * debit_note: used on sale and purchase journals but with lower\
        priority than invoices.\
        * credit_note: used on sale_refund and purchase_refund journals.\
        * ticket: automatically loaded for purchase journals but only loaded\
        on sales journals if point_of_sale is fiscal_printer\
        * receipt_invoice: mean to be used as invoices but not automatically\
        loaded because it is not usually used\
        * in_document: automatically loaded for purchase journals but not \
        loaded on sales journals. Also can be selected on partners, to be \
        available it must be selected on partner.\
        ')
    active = fields.Boolean(
        'Active', default=True)


class afip_document_letter(models.Model):
    _name = 'afip.document_letter'
    _description = 'Afip Document letter'

    name = fields.Char(
        'Name', size=64, required=True)
    afip_document_class_ids = fields.One2many(
        'afip.document_class', 'document_letter_id', 'Afip Document Classes')
    issuer_ids = fields.Many2many(
        'afip.responsability', 'afip_doc_letter_issuer_rel',
        'letter_id', 'responsability_id', 'Issuers',)
    receptor_ids = fields.Many2many(
        'afip.responsability', 'afip_doc_letter_receptor_rel',
        'letter_id', 'responsability_id', 'Receptors',)
    active = fields.Boolean(
        'Active', default=True)
    vat_discriminated = fields.Boolean(
        'Vat Discriminated on Invoices?',
        help="If True, the vat will be discriminated on invoice report.")

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'), ]


class afip_responsability(models.Model):
    _name = 'afip.responsability'
    _description = 'AFIP VAT Responsability'

    name = fields.Char(
        'Name', size=64, required=True)
    code = fields.Char(
        'Code', size=8, required=True)
    active = fields.Boolean(
        'Active', default=True)
    issued_letter_ids = fields.Many2many(
        'afip.document_letter', 'afip_doc_letter_issuer_rel',
        'responsability_id', 'letter_id', 'Issued Document Letters')
    received_letter_ids = fields.Many2many(
        'afip.document_letter', 'afip_doc_letter_receptor_rel',
        'responsability_id', 'letter_id', 'Received Document Letters')
    vat_tax_required_on_sales_invoices = fields.Boolean(
        'VAT Tax Required on Sales Invoices?',
        help='If True, then a vay tax is mandatory on each sale invoice for companies of this responsability',
        )

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'),
                        ('code', 'unique(code)', 'Code must be unique!')]


class afip_document_type(models.Model):
    _name = 'afip.document_type'
    _description = 'AFIP document types'

    name = fields.Char(
        'Name', size=120, required=True)
    code = fields.Char(
        'Code', size=16, required=True)
    afip_code = fields.Integer(
        'AFIP Code', required=True)
    active = fields.Boolean(
        'Active', default=True)
