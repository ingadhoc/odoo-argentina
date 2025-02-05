# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    l10n_ar_fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Fiscal Position",
        check_company=True,
        compute="_compute_fiscal_position_id",
        store=True,
        readonly=False,
        domain=[("l10n_ar_tax_ids.tax_type", "=", "withholding")],
    )

    @api.depends("line_ids", "partner_id")
    def _compute_fiscal_position_id(self):
        for rec in self:
            if (
                rec.partner_type != "supplier"
                or rec.country_code != "AR"
                or not rec.can_edit_wizard
                or (rec.can_group_payments and not rec.group_payment)
            ):
                rec.l10n_ar_fiscal_position_id = False
                continue
            # si estamos pagando todas las facturas de misma delivery address usamos este dato para computar la
            # fiscal position
            if len(rec.batches) == 1:
                batch_result = rec.batches[0]
                addresses = batch_result["lines"].mapped("move_id.partner_shipping_id")
                if len(addresses) == 1:
                    address = addresses
                else:
                    address = rec.partner_id
            rec.l10n_ar_fiscal_position_id = (
                self.env["account.fiscal.position"].with_company(rec.company_id)._get_fiscal_position(address)
            )

    @api.depends("l10n_ar_fiscal_position_id")
    def _compute_l10n_ar_withholding_ids(self):
        """Para compatibilidad si no se usa payment pro en la compania"""
        # no llamamos a super porque ahora estamos trabajando con fiscal positions
        # y solo agregamos taxes segun la FP que corresponda
        # super()._compute_l10n_ar_withholding_ids()
        # taxes = self.l10n_ar_withholding_ids.mapped('tax_id')
        date = fields.Date.from_string(self.payment_date) or datetime.date.today()

        withholdings = [Command.clear()]
        if self.l10n_ar_fiscal_position_id.l10n_ar_tax_ids:
            taxes = self.l10n_ar_fiscal_position_id._l10n_ar_add_taxes(
                self.partner_id, self.company_id, date, "withholding"
            )
            withholdings += [Command.create({"tax_id": x.id}) for x in taxes]
        self.l10n_ar_withholding_ids = withholdings
