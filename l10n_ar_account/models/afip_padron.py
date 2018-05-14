from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)


class AccountConcept(models.Model):
    _name = "afip.concept"

    code = fields.Char(
        'Code',
        required=True
    )
    name = fields.Char(
        'Name',
        required=True
    )
    active = fields.Boolean(
        default=True,
    )


class AccountActivity(models.Model):
    _name = "afip.activity"

    code = fields.Char(
        'Code',
        required=True
    )
    name = fields.Char(
        'Name',
        required=True
    )
    active = fields.Boolean(
        default=True,
    )


class AccountTax(models.Model):
    _name = "afip.tax"

    code = fields.Char(
        'Code',
        required=True
    )
    name = fields.Char(
        'Name',
        required=True
    )
    active = fields.Boolean(
        default=True,
    )
