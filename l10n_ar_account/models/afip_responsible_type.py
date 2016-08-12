# -*- coding: utf-8 -*-
from openerp import fields, models
# from openerp.exceptions import UserError


class AfipResponsibleType(models.Model):
    _name = 'afip.responsible.type'
    _description = 'AFIP Responsible Type'
    _order = 'sequence'

    name = fields.Char(
        'Name',
        size=64,
        required=True
        )
    sequence = fields.Integer(
        'Sequence',
        )
    code = fields.Char(
        'Code',
        size=8,
        required=True
        )
    active = fields.Boolean(
        'Active',
        default=True
        )
    issued_letter_ids = fields.Many2many(
        'account.document.letter',
        'account_document_letter_responsible_issuer_rel',
        'afip_responsible_type_id',
        'letter_id',
        'Issued Document Letters'
        )
    received_letter_ids = fields.Many2many(
        'account.document.letter',
        'account_document_letter_responsible_receptor_rel',
        'afip_responsible_type_id',
        'letter_id',
        'Received Document Letters'
        )

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'),
                        ('code', 'unique(code)', 'Code must be unique!')]
