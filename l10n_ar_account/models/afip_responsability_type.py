# -*- coding: utf-8 -*-
from odoo import fields, models
# from odoo.exceptions import UserError


class AfipresponsabilityType(models.Model):
    _name = 'afip.responsability.type'
    _description = 'AFIP Responsability Type'
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
        'account_doc_let_responsability_issuer_rel',
        'afip_responsability_type_id',
        'letter_id',
        'Issued Document Letters'
    )
    received_letter_ids = fields.Many2many(
        'account.document.letter',
        'account_doc_let_responsability_receptor_rel',
        'afip_responsability_type_id',
        'letter_id',
        'Received Document Letters'
    )

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'),
                        ('code', 'unique(code)', 'Code must be unique!')]
