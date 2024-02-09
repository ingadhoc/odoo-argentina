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

    withholding_id = fields.Many2one('l10n_ar.payment.withholding', compute='_compute_withholding')

    def _compute_withholding(self):
        for rec in self:
            if rec.tax_line_id and rec.payment_id:
                rec.withholding_id = rec.payment_id.l10n_ar_withholding_line_ids.filtered(lambda x: x.tax_id == rec.tax_line_id)
            else:
                rec.withholding_id = False
