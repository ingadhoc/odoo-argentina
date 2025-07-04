from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    _inherit = "account.tax"

    ratio = fields.Float(default=100.00, help="Ratio to apply to tax base amount.")

    @api.constrains("ratio")
    def _check_line_ids_percent(self):
        """Check that the total percent is not bigger than 100.0"""
        for tax in self:
            if not tax.ratio or tax.ratio < 0.0 or tax.ratio > 100.0:
                raise ValidationError(
                    self.env._(
                        "The total percentage (%s) should be greater than 0 and less than or equal to 100.", tax.ratio
                    )
                )
