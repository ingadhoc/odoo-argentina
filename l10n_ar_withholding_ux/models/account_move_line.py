##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
# import odoo.addons.decimal_precision as dp
# from odoo.exceptions import ValidationError
# from dateutil.relativedelta import relativedelta
# import datetime


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # automatic = fields.Boolean(
    # )
    # withholding_accumulated_payments = fields.Selection(
    #     related='tax_line_id.withholding_accumulated_payments',
    # )
    # TODO todo esto deberia ir a un json
    # de hecho podemos revisar y lo que no necesitemos consultar para operar, podemos guardarlo en un memo, chatter o similar
    withholdable_invoiced_amount = fields.Float('Importe imputado sujeto a retencion', readonly=True,)
    withholdable_advanced_amount = fields.Float('Importe a cuenta sujeto a retencion',)
    accumulated_amount = fields.Float(readonly=True,)
    total_amount = fields.Float(readonly=True,)
    withholding_non_taxable_minimum = fields.Float('Non-taxable Minimum', readonly=True,)
    withholding_non_taxable_amount = fields.Float('Non-taxable Amount', readonly=True,)
    withholdable_base_amount = fields.Float(readonly=True,)
    period_withholding_amount = fields.Float(readonly=True,)
    previous_withholding_amount = fields.Float(readonly=True,)
    computed_withholding_amount = fields.Float(readonly=True,)
