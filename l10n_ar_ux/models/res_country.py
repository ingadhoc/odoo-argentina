from odoo import _, api, models
from odoo.exceptions import ValidationError


class ResCountry(models.Model):
    _inherit = "res.country"

    @api.constrains("code")
    def _check_argentina_code(self):
        argentina = self.env.ref("base.ar", raise_if_not_found=False)
        for record in self:
            if argentina and record.id == argentina.id and record.code != "AR":
                raise ValidationError(_("Argentina country code must always be 'AR'."))
