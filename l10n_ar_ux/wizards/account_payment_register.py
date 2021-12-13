# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_latam_check_printing_type = fields.Selection(related='l10n_latam_checkbook_id.check_printing_type')
