from odoo import models, fields, api, _
from odoo.exceptions import UserError
# from odoo.addons.l10n_ar_account.models import account_journal
try:
    from pyafipws.padron import PadronAFIP
except ImportError:
    PadronAFIP = None


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    arba_cit = fields.Char(
        related='company_id.arba_cit'
    )
    # point_of_sale_type = fields.Selection(
    #     account_journal.AccountJournal._point_of_sale_types_selection,
    #     'Point Of Sale Type',
    #     default='manual',
    # )
    # point_of_sale_number = fields.Integer(
    #     'Point Of Sale Number',
    #     help='On Argentina Localization with use documents and sales '
    #     'journals is mandatory'
    # )
    # afip_responsability_type_id = fields.Many2one(
    #     related='company_id.afip_responsability_type_id',
    # )

    # @api.multi
    # def set_chart_of_accounts(self):
    #     """
    #     We send this value in context because to use them on journals
    #     creation
    #     """
    #     if self.point_of_sale_type and not self.point_of_sale_number:
    #         raise UserError(_('Debe indicar un número de punto de venta'))
    #     return super(AccountConfigSettings, self.with_context(
    #         sale_use_documents=self.sale_use_documents,
    #         purchase_use_documents=self.purchase_use_documents,
    #         point_of_sale_number=self.point_of_sale_number,
    #         point_of_sale_type=self.point_of_sale_type,
    #     )).set_chart_of_accounts()

    @api.multi
    def refresh_taxes_from_padron(self):
        self.refresh_from_padron("impuestos")

    @api.multi
    def refresh_concepts_from_padron(self):
        self.refresh_from_padron("conceptos")

    @api.multi
    def refresh_activities_from_padron(self):
        self.refresh_from_padron("actividades")

    @api.model
    def refresh_from_padron(self, resource_type):
        """
        resource_type puede ser "impuestos", "conceptos", "actividades",
        "caracterizaciones", "categoriasMonotributo", "categoriasAutonomo".
        """
        if resource_type == 'impuestos':
            model = 'afip.tax'
        elif resource_type == 'actividades':
            model = 'afip.activity'
        elif resource_type == 'conceptos':
            model = 'afip.concept'
        else:
            raise UserError(_('Resource Type %s not implemented!') % (
                resource_type))
        padron = PadronAFIP()
        separator = ';'
        data = padron.ObtenerTablaParametros(resource_type, separator)
        codes = []
        for line in data:
            code, name = line.split(separator)[1:3]
            vals = {
                'code': code,
                'name': name,
                'active': True,
            }
            record = self.env[model].search([('code', '=', code)], limit=1)
            codes.append(code)
            if record:
                record.write(vals)
            else:
                record.create(vals)
        # deactivate the ones that are not in afip
        self.env[model].search([('code', 'not in', codes)]).write(
            {'active': False})
