from odoo import models, fields


class AccountDocumentLetter(models.Model):
    _name = 'account.document.letter'
    _description = 'Account Document Letter'

    name = fields.Char(
        'Name',
        required=True
    )
    document_type_ids = fields.One2many(
        'account.document.type',
        'document_letter_id',
        'Document Types',
        auto_join=True,
    )
    issuer_ids = fields.Many2many(
        'afip.responsability.type',
        'account_document_letter_responsability_issuer_rel',
        'document_letter_id',
        'afip_responsability_type_id',
        'Issuers',
        auto_join=True,
    )
    receptor_ids = fields.Many2many(
        'afip.responsability.type',
        'account_document_letter_responsability_receptor_rel',
        'document_letter_id',
        'afip_responsability_type_id',
        'Receptors',
        auto_join=True,
    )
    active = fields.Boolean(
        'Active',
        default=True
    )
    taxes_included = fields.Boolean(
        'Taxes Included?',
        help='Documents related to this letter will include taxes on reports',
    )
    # taxes_discriminated = fields.Boolean(
    #     'Taxes Discriminated on Invoices?',
    #     help="If True, the taxes will be discriminated on invoice report.")

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'), ]
