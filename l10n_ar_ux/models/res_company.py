##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    gross_income_jurisdiction_ids = fields.Many2many(
        related='partner_id.gross_income_jurisdiction_ids',
        readonly=False,
    )
    # TODO this field could be defined directly on l10n_ar_account_withholding
    arba_cit = fields.Char(
        'CIT ARBA',
        help='Clave de Identificación Tributaria de ARBA',
    )
    # la fecha de comienzo de actividades puede ser por cada punto de venta distinta, lo convertimos a related del
    # partner
    l10n_ar_afip_start_date = fields.Date(
        related='partner_id.start_date', string='Activities Start', readonly=False)
    l10n_ar_report_signature = fields.Image('Firma', copy=False, attachment=True)
    l10n_ar_report_signed_by = fields.Text('Aclaracion', copy=False)
    l10n_ar_invoice_report_ars_amount = fields.Boolean('Mostrar importe equivalente en ARS', default=False)
