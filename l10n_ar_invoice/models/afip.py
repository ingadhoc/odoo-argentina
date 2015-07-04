# -*- coding: utf-8 -*-
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

    name = fields.Char(
        'Name', required=True)
    number = fields.Integer(
        'Number', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'afip.point_of_sale'),)
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
        string='Documents Classes',
        )

    @api.one
    @api.depends('journal_ids.journal_document_class_ids')
    def get_journal_document_class_ids(self):
        journal_document_class_ids = self.env[
            'account.journal.afip_document_class'].search([
                ('journal_id.point_of_sale_id', '=', self.id)])
        self.journal_document_class_ids = journal_document_class_ids

    _sql_constraints = [('number_unique', 'unique(number, company_id)',
                         'Number Must be Unique per Company!'), ]

    @api.one
    def generate_purchase_journals(self):
        actual_types = self.journal_ids.mapped('type')
        vals = {
            'name': "Facturas Compra %s" % self.name,
            'code': "FAC%02i" % self.number,
            'type': 'purchase',
            'point_of_sale_id': self.id,
            'company_id': self.company_id.id,
            'use_documents': True,
        }
        if 'purchase' not in actual_types:
            _logger.info('Creating purchase journal with vals %s' % str(vals))
            self.journal_ids.create(vals)

        if 'purchase_refund' not in actual_types:
            _logger.info('Creating purchase_refund journal with vals %s' % str(vals))
            vals.update({
                'name': "NC Compra %s" % self.name,
                'code': "NCC%02i" % self.number,
                'type': 'purchase_refund',
            })
            self.journal_ids.create(vals)

    @api.one
    def generate_sale_journals(self):
        actual_types = self.journal_ids.mapped('type')
        vals = {
            'name': "Facturas Vta %s" % self.name,
            'code': "FAV%02i" % self.number,
            'type': 'sale',
            'point_of_sale_id': self.id,
            'company_id': self.company_id.id,
            'use_documents': True,
        }
        if 'sale' not in actual_types:
            _logger.info('Creating sale journal with vals %s' % str(vals))
            self.journal_ids.create(vals)

        if 'sale_refund' not in actual_types:
            _logger.info('Creating sale_refund journal with vals %s' % str(vals))
            vals.update({
                'name': "NC Vta %s" % self.name,
                'code': "NCV%02i" % self.number,
                'type': 'sale_refund',
            })
            self.journal_ids.create(vals)


class afip_document_class(models.Model):
    _name = 'afip.document_class'
    _description = 'Afip Document Class'

    name = fields.Char(
        'Name', size=120)
    doc_code_prefix = fields.Char(
        'Document Code Prefix', help="Prefix for Documents Codes on Invoices \
        and Account Moves. For eg. 'FA ' will build 'FA 0001-0000001' Document Number")
    code_template = fields.Char(
        'Code Template for Journal')
    afip_code = fields.Integer(
        'AFIP Code', required=True)
    document_letter_id = fields.Many2one(
        'afip.document_letter', 'Document Letter')
    report_name = fields.Char(
        'Name on Reports',
        help='Name that will be printed in reports, for example "CREDIT NOTE"')
    document_type = fields.Selection(
        [('invoice', 'Invoices'), ('credit_note', 'Credit Notes'),
         ('debit_note', 'Debit Notes'), ('other_document', 'Other Documents')],
        string='Document Type',
        help='It defines some behaviours on automatic journal selection and\
        in menus where it is shown.')
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

    @api.one
    @api.constrains('product_types')
    def _check_product_types(self):
        if self.product_types:
            types = set(self.product_types.split(','))
            if not types.issubset(['adjust', 'consu', 'service']):
                raise Warning(_('You provided an invalid list of product types.\
                Must been separated by commas'))
