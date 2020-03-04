from odoo import models, fields


class AccountConcept(models.Model):
    _name = "afip.concept"
    _description = "afip.concept"

    code = fields.Char(required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class AccountActivity(models.Model):
    _name = "afip.activity"
    _description = "afip.activity"

    code = fields.Char(required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class AccountTax(models.Model):
    _name = "afip.tax"
    _description = "afip.tax"

    code = fields.Char(required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
