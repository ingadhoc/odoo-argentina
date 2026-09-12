# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import Command, _, api, fields, models

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
    fiscal_position_mode = fields.Selection(
        [("automatic", "Automatic"), ("manual", "Manual")],
        default="automatic",
        required=True,
    )
    is_payment_pro = fields.Boolean(
        default=lambda self: bool(self.env.context.get("payment_pro")),
    )

    def _is_check_or_bundle(self, payment_method_code, check_subtype=False):
        if check_subtype == "move_check":
            codes = ["in_third_party_checks", "out_third_party_checks", "return_third_party_checks"]
        elif check_subtype == "new_check":
            codes = ["new_third_party_checks", "own_checks"]
        else:
            codes = [
                "in_third_party_checks",
                "out_third_party_checks",
                "return_third_party_checks",
                "new_third_party_checks",
                "own_checks",
                "payment_bundle",
            ]
        return payment_method_code in codes

    @api.depends("line_ids", "partner_id", "fiscal_position_mode")
    def _compute_fiscal_position_id(self):
        for rec in self:
            # En modo manual el usuario elige la FP directamente; no recomputamos
            if rec.fiscal_position_mode == "manual":
                continue
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
        for rec in self:
            date = rec.payment_date or fields.Date.context_today(rec)

            withholdings = [Command.clear()]
            if rec.l10n_ar_fiscal_position_id.l10n_ar_tax_ids:
                taxes = rec.l10n_ar_fiscal_position_id._l10n_ar_add_taxes(
                    rec.partner_id, rec.company_id, date, "withholding"
                )
                withholdings += [Command.create({"tax_id": x.id}) for x in taxes]
            rec.l10n_ar_withholding_ids = withholdings

    @api.depends("is_payment_pro", "payment_type")
    def _compute_available_journal_ids(self):
        super()._compute_available_journal_ids()
        for wizard in self:
            if not wizard.is_payment_pro or not wizard.payment_type:
                # Skip filtering if payment_type is not yet resolved (e.g. during
                # precompute of journal_id) to avoid resetting journal_id to False.
                continue
            direction = wizard.payment_type
            wizard.available_journal_ids = wizard.available_journal_ids.filtered(
                lambda j: any(
                    not wizard._is_check_or_bundle(l.payment_method_id.code)
                    for l in j._get_available_payment_method_lines(direction)
                )
            )

    @api.depends("is_payment_pro")
    def _compute_journal_id(self):
        super()._compute_journal_id()
        for wizard in self:
            if not wizard.is_payment_pro:
                continue
            if wizard.journal_id not in wizard.available_journal_ids:
                wizard.journal_id = wizard.available_journal_ids[:1]

    @api.depends("is_payment_pro")
    def _compute_payment_method_line_fields(self):
        super()._compute_payment_method_line_fields()
        for wizard in self:
            if not wizard.is_payment_pro:
                continue
            wizard.available_payment_method_line_ids = wizard.available_payment_method_line_ids.filtered(
                lambda l: not wizard._is_check_or_bundle(l.payment_method_id.code)
            )

    @api.depends("is_payment_pro")
    def _compute_payment_method_line_id(self):
        super()._compute_payment_method_line_id()
        for wizard in self:
            if not wizard.is_payment_pro:
                continue
            if wizard.payment_method_line_id not in wizard.available_payment_method_line_ids:
                wizard.payment_method_line_id = wizard.available_payment_method_line_ids[:1]

    def _get_debt_line_ids_cmd(self, batch_result):
        valid_types = {"asset_receivable", "liability_payable"}
        debt_lines = batch_result["lines"].filtered(lambda l: l.account_id.account_type in valid_types)
        return [Command.set(debt_lines.ids)] if debt_lines else []

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if not self.is_payment_pro:
            return payment_vals
        # Strip withholding write_off entries — the payment's l10n_ar_withholding_line_ids
        # creates the journal lines via _prepare_move_withholding_lines at action_post time.
        payment_vals["write_off_line_vals"] = [
            v
            for v in payment_vals.get("write_off_line_vals", [])
            if not v.get("tax_repartition_line_id") and not v.get("tax_ids")
        ]
        # Embed to_pay_move_line_ids so l10n_ar_fiscal_position_id resolves at payment
        # creation time, triggering withholding computation before action_post.
        debt_cmd = self._get_debt_line_ids_cmd(batch_result)
        if debt_cmd:
            payment_vals.setdefault("to_pay_move_line_ids", debt_cmd)
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        if not self.is_payment_pro:
            return payment_vals
        # Same as wizard path: embed to_pay_move_line_ids for multi-partner batches.
        debt_cmd = self._get_debt_line_ids_cmd(batch_result)
        if debt_cmd:
            payment_vals.setdefault("to_pay_move_line_ids", debt_cmd)
        return payment_vals

    def _init_payments(self, to_process, edit_mode=False):
        if self.env.context.get("payment_pro_draft"):
            for vals in to_process:
                for key in ("write_off_line_vals", "force_balance", "line_ids"):
                    vals["create_vals"].pop(key, None)
        payments = super()._init_payments(to_process, edit_mode=edit_mode)
        if not self.is_payment_pro:
            return payments
        # Flush pending stored computed fields (l10n_ar_withholding_line_ids,
        # withholdings_amount) triggered by to_pay_move_line_ids set at creation.
        self.env.flush_all()
        # amount must equal (to_pay_amount - withholdings_amount) so that:
        #   payment_total = amount + withholdings_amount == to_pay_amount
        # For single-partner, l10n_ar_withholding already reduces the wizard amount;
        # for multi-partner batches the wizard carries no withholdings, so we correct here.
        for vals in to_process:
            payment = vals["payment"]
            withholdings = getattr(payment, "withholdings_amount", 0.0)
            if not withholdings:
                continue
            net = payment.to_pay_amount - withholdings
            if net > 0 and not payment.currency_id.is_zero(net - payment.amount):
                payment.write({"amount": net, "amount_exact": net})
        return payments

    def _post_payments(self, to_process, edit_mode=False):
        if not self.env.context.get("payment_pro_draft"):
            return super()._post_payments(to_process, edit_mode=edit_mode)

    def _reconcile_payments(self, to_process, edit_mode=False):
        valid_types = {"asset_receivable", "liability_payable"}
        for vals in to_process:
            payment = vals["payment"]
            if payment.company_id.use_payment_pro:
                debt_lines = vals["to_reconcile"].filtered(lambda l: l.account_id.account_type in valid_types)
                if debt_lines and not payment.to_pay_move_line_ids:
                    payment.to_pay_move_line_ids = [Command.set(debt_lines.ids)]
        if not self.env.context.get("payment_pro_draft"):
            return super()._reconcile_payments(to_process, edit_mode=edit_mode)

    def _create_payments(self):
        payments = super(AccountPaymentRegister, self.with_context(skip_to_pay_compute=True))._create_payments()
        if self.fiscal_position_mode == "manual" and self.l10n_ar_fiscal_position_id:
            payments.l10n_ar_fiscal_position_id = self.l10n_ar_fiscal_position_id
        return payments

    def action_create_and_confirm(self):
        return self.action_create_payments()

    def action_create_draft(self):
        payments = self.with_context(payment_pro_draft=True)._create_payments()
        return {
            "name": _("Payments"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", payments.ids)],
            "context": {"create": False},
            "target": "current",
        }
