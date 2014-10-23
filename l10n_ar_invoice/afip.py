# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from openerp.exceptions import Warning


class afip_point_of_sale(models.Model):
    _name = 'afip.point_of_sale'
    _description = 'Afip Point Of Sale'

    @api.one
    @api.depends('number')
    def _get_code(self):
        code = False
        if self.number:
            # TODO rellenar el number a cuatro
            code = str(self.number)
        self.code = code
    name = fields.Char(
        'Name', required=True)
    number = fields.Integer(
        'Number', required=True)
    code = fields.Char(
        'Code', compute="_get_code")
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'afip.point_of_sale'),)

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


class afip_concept_type(models.Model):
    _name = 'afip.concept_type'
    _description = 'AFIP concept types'

    name = fields.Char(
        'Name', size=120, required=True)
    afip_code = fields.Integer(
        'AFIP Code', required=True)
    active = fields.Boolean(
        'Active', default=True)
    product_types = fields.Char(
        'Product types',
        help='Translate this product types to this AFIP concept.\
        Types must be a subset of adjust,\
        consu and service separated by commas.',
        required=True)

    @api.one
    @api.constrains('product_types')
    def _check_product_types(self):
        if self.product_types:
            types = set(self.product_types.split(','))
            if not types.issubset(['adjust', 'consu', 'service']):
                raise Warning(_('You provided an invalid list of product types.\
                Must been separated by commas'))


class afip_optional_type(models.Model):
    _name = 'afip.optional_type'
    _description = 'AFIP optional types'

    name = fields.Char(
        'Name', size=120, required=True)
    afip_code = fields.Integer(
        'AFIP Code', required=True)
    apply_rule = fields.Char(
        'Apply rule')
    value_computation = fields.Char(
        'Value computation')
    active = fields.Boolean(
        'Active', default=True)
