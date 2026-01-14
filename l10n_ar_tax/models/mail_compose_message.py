import base64

from odoo import models
from odoo.tools import safe_eval


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _prepare_mail_values(self, res_ids):
        """Extended to add withholding attachments when sending payments by email."""
        mail_values_all = super()._prepare_mail_values(res_ids)

        if self.model != "account.payment":
            return mail_values_all

        report = self.env.ref(
            "l10n_ar_tax.action_report_withholding_certificate",
            raise_if_not_found=False,
        )
        if not report:
            return mail_values_all

        # Check if we're in mass_mail mode (uses commands) or comment mode (uses plain IDs)
        email_mode = self.composition_mode == "mass_mail"

        payments = self.env["account.payment"].browse(res_ids).filtered(lambda p: p.partner_type == "supplier")
        for payment in payments:
            if payment.id not in mail_values_all:
                continue

            # Get existing attachments
            attachment_ids = mail_values_all[payment.id].get("attachment_ids", [])

            for withholding in payment.l10n_ar_withholding_line_ids.filtered("amount"):
                try:
                    report_name = safe_eval.safe_eval(report.print_report_name, {"object": withholding})
                    report_content, _ = self.env["ir.actions.report"]._render(report.report_name, withholding.ids)
                    report_content_encoded = base64.b64encode(report_content)

                    attachment = self.env["ir.attachment"].create(
                        {
                            "name": report_name,
                            "datas": report_content_encoded,
                            "res_model": "mail.message",
                            "res_id": 0,
                            "type": "binary",
                        }
                    )

                    # In mass_mail mode use commands (4, id), in comment mode use plain IDs
                    if email_mode:
                        attachment_ids.append((4, attachment.id))
                    else:
                        attachment_ids.append(attachment.id)

                except Exception:
                    continue

            mail_values_all[payment.id]["attachment_ids"] = attachment_ids

        return mail_values_all
