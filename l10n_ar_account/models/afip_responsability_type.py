from odoo import fields, models
# from odoo.exceptions import UserError


class AfipresponsabilityType(models.Model):
    _name = 'afip.responsability.type'
    _description = 'AFIP Responsability Type'
    _order = 'sequence'

    name = fields.Char(
        'Name',
        size=64,
        required=True,
        index=True,
    )
    sequence = fields.Integer(
        'Sequence',
    )
    code = fields.Char(
        'Code',
        size=8,
        required=True,
        index=True,
    )
    active = fields.Boolean(
        'Active',
        default=True
    )
    issued_letter_ids = fields.Many2many(
        'account.document.letter',
        'account_doc_let_responsability_issuer_rel',
        'afip_responsability_type_id',
        'letter_id',
        'Issued Document Letters',
        auto_join=True,
    )
    received_letter_ids = fields.Many2many(
        'account.document.letter',
        'account_doc_let_responsability_receptor_rel',
        'afip_responsability_type_id',
        'letter_id',
        'Received Document Letters',
        auto_join=True,
    )
    # hacemos esto para que, principalmente, monotributistas y exentos no
    # requieran iva, otra forma sería poner el impuesto no corresponde, pero
    # no queremos complicar vista y configuración con un impuesto que no va
    # a aportar nada
    company_requires_vat = fields.Boolean(
        string='Company requires vat?',
        help='Companies of this type will require VAT tax on every invoice '
        'line of a journal that use documents'
    )

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'),
                        ('code', 'unique(code)', 'Code must be unique!')]
