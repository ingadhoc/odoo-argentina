##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    jurisdiction_code = fields.Char(compute="_compute_jurisdiction_code")

    @api.depends()
    def _compute_jurisdiction_code(self):
        for rec in self:
            if rec.country_id.code == "AR":
                rec.jurisdiction_code = {
                    "B": "902",
                    "K": "903",
                    "H": "906",
                    "U": "907",
                    "C": "901",
                    "W": "905",
                    "X": "904",
                    "E": "908",
                    "P": "909",
                    "Y": "910",
                    "L": "911",
                    "F": "912",
                    "M": "913",
                    "N": "914",
                    "Q": "915",
                    "R": "916",
                    "A": "917",
                    "J": "918",
                    "D": "919",
                    "Z": "920",
                    "S": "921",
                    "G": "922",
                    "V": "923",
                    "T": "924",
                }.get(rec.code, False)
            else:
                rec.jurisdiction_code = False
