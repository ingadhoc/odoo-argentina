from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Override to add tracking
    l10n_ar_afip_responsibility_type_id = fields.Many2one(tracking=True)

    gross_income_jurisdiction_ids = fields.Many2many(
        "res.country.state",
        string="Gross Income Jurisdictions",
        help="The state of the company is cosidered the main jurisdiction",
    )

    # ARCA Padron
    start_date = fields.Date("Activities Start")
    estado_padron = fields.Char("Estado ARCA")
    imp_ganancias_padron = fields.Selection(
        [("NI", "No Inscripto"), ("AC", "Activo"), ("EX", "Exento"), ("NC", "No corresponde")], "Ganancias"
    )
    imp_iva_padron = fields.Selection(
        [
            ("NI", "No Inscripto"),
            ("AC", "Activo"),
            ("EX", "Exento"),
            ("NA", "No alcanzado"),
            ("XN", "Exento no alcanzado"),
            ("AN", "Activo no alcanzado"),
        ],
        "IVA",
    )
    integrante_soc_padron = fields.Selection([("N", "No"), ("S", "Si")], "Integrante Sociedad")
    monotributo_padron = fields.Selection([("N", "No"), ("S", "Si")], "Monotributo")
    actividad_monotributo_padron = fields.Char()
    empleador_padron = fields.Boolean()
    impuestos_padron = fields.Many2many(
        "afip.tax", "res_partner_afip_tax_rel", "partner_id", "afip_tax_id", "Impuestos"
    )
    last_update_padron = fields.Date()

    @api.constrains("gross_income_jurisdiction_ids", "state_id")
    def check_gross_income_jurisdictions(self):
        for rec in self:
            if rec.state_id and rec.state_id in rec.gross_income_jurisdiction_ids:
                raise ValidationError(
                    _(
                        "Jurisdiction %s is considered the main jurisdiction "
                        "because it is the state of the company, please remove it "
                        "from the jurisdiction list"
                    )
                    % rec.state_id.name
                )
