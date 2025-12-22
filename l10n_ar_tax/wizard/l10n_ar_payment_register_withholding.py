# pylint: disable=protected-access
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class L10n_ArPaymentRegisterWithholding(models.TransientModel):
    _inherit = "l10n_ar.payment.register.withholding"

    # Para que computen bien al computarse automáticamente las retenciones, estos dos campos NO deberian ser requeridos
    # o deberian tener pre-compute
    base_amount = fields.Monetary(required=False)
    amount = fields.Monetary(required=False)
