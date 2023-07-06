
from odoo import fields, models


class AccounTpaymentAddChecks(models.TransientModel):
    _name = "account.payment.add.checks"
    _description = "account.payment.add.checks"

    check_ids = fields.Many2many(comodel_name="account.payment")
    company_id = fields.Many2one('res.company')

    def confirm(self):
        self.ensure_one()
        payment_group = self.env["account.payment.group"].browse(self.env.context.get("active_id", False))
        if payment_group:
            vals_list = [{
                'l10n_latam_check_id': check.id,
                'amount': check.amount,
                'partner_id': payment_group.partner_id.id,
                'payment_group_id': payment_group.id,
                'payment_type': 'outbound',
                'partner_type': payment_group.partner_type,
                'journal_id': check.l10n_latam_check_current_journal_id.id,
                'payment_method_line_id': check.l10n_latam_check_current_journal_id._get_available_payment_method_lines(
                    'oubound').filtered(lambda x: x.code == 'out_third_party_checks').id,
            } for check in self.check_ids]
            self.env['account.payment'].create(vals_list)

        return {"type": "ir.actions.act_window_close"}
