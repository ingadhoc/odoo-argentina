from odoo import api, fields, models


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

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Activity code must be unique"),
        ("code_length", "CHECK(LENGTH(code) <= 6)", "Activity codes must be at most 6 characters long"),
    ]

    @api.depends("code", "name")
    @api.depends_context("formatted_display_name")
    def _compute_display_name(self):
        for activity in self:
            if activity.env.context.get("formatted_display_name"):
                activity.display_name = f"--{activity.code}--\t{activity.name}"
            else:
                activity.display_name = f"{activity.code} - {activity.name}"


class AccountTax(models.Model):
    _name = "afip.tax"
    _description = "afip.tax"

    code = fields.Char(required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
