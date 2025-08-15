import base64

from odoo import models
from odoo.tools import safe_eval


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _compute_attachment_ids(self):
        """Extends original method so it is possible to attach and previsualize
        withholding vouchers when sending payment reports by email."""
        super()._compute_attachment_ids()
        for composer in self:
            res_ids = composer._evaluate_res_ids() or [0]
            if composer.model == "account.payment" and composer.template_id and len(res_ids) == 1:
                payment = self.env[composer.model].browse(res_ids)
                if payment.partner_type != "supplier":
                    return

                report = self.env.ref("l10n_ar_tax.action_report_withholding_certificate", raise_if_not_found=False)
                if not report:
                    return

                attachments = []
                for withholding in payment.l10n_ar_withholding_line_ids.filtered("amount"):
                    report_name = safe_eval.safe_eval(report.print_report_name, {"object": withholding})
                    result, _ = self.env["ir.actions.report"]._render(report.report_name, withholding.ids)
                    file = base64.b64encode(result)

                    attachment = self.env["ir.attachment"].create(
                        {
                            "name": report_name,
                            "datas": file,
                            "res_model": "mail.compose.message",
                            "res_id": 0,
                            "type": "binary",
                        }
                    )
                    attachments.append(attachment.id)

                if attachments:
                    composer.attachment_ids = [(6, 0, composer.attachment_ids.ids + attachments)]
