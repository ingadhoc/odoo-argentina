import base64

from odoo import models
from odoo.tools import safe_eval


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _compute_attachment_ids(self):
        """Extends original method so it is possible to attach and preview
        withholding vouchers when sending payment reports by email.
        Only works for SINGLE payment sending (preview mode)."""
        super()._compute_attachment_ids()
        for composer in self:
            res_ids = composer._evaluate_res_ids() or [0]
            if (
                composer.model != "account.payment"
                or not composer.template_id
                or len(res_ids) != 1  # Solo para un pago
            ):
                continue

            report = self.env.ref(
                "l10n_ar_tax.action_report_withholding_certificate",
                raise_if_not_found=False,
            )
            if not report:
                continue

            payment = self.env["account.payment"].browse(res_ids)
            if payment.partner_type != "supplier":
                continue

            attachments = []
            for withholding in payment.l10n_ar_withholding_line_ids.filtered("amount"):
                # Importante: si se modifica la manera de acceder al report_name acá, hay que modificarlo
                # también en el método _prepare_mail_values
                report_name = safe_eval.safe_eval(report.print_report_name, {"object": withholding})
                report_content, _ = self.env["ir.actions.report"]._render(report.report_name, withholding.ids)
                report_content_encoded = base64.b64encode(report_content)

                # Crear adjunto temporal para previsualización
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": report_name,
                        "datas": report_content_encoded,
                        "res_model": "mail.compose.message",
                        "res_id": composer.id,
                        "type": "binary",
                    }
                )
                attachments.append(attachment.id)

            if attachments:
                composer.attachment_ids = [(6, 0, composer.attachment_ids.ids + attachments)]

    def _prepare_mail_values(self, res_ids):
        """Extended to add withholding attachments when sending payments by email.
        Handles BOTH single (reuses preview attachments) and mass sending (creates new)."""
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

            # Get existing attachments from parent method
            attachment_ids = mail_values_all[payment.id].get("attachment_ids", [])

            for withholding in payment.l10n_ar_withholding_line_ids.filtered("amount"):
                try:
                    report_name = safe_eval.safe_eval(report.print_report_name, {"object": withholding})

                    # CASO 1: Envío individual - reutilizar adjuntos creados en compute
                    if len(res_ids) == 1:
                        # Buscar adjunto existente creado en la previsualización
                        existing_attachment = self.attachment_ids.filtered(
                            lambda a: a.name == report_name
                            and a.res_model == "mail.compose.message"
                            and a.res_id == self.id
                        )

                        # Reutilizar:  cambiar res_model para que se vincule al mensaje
                        existing_attachment[0].write(
                            {
                                "res_model": "mail.message",
                                "res_id": 0,
                            }
                        )
                        attachment = existing_attachment[0]

                    # CASO 2: Envío masivo - crear adjuntos directamente (sin previsualización previa)
                    else:
                        # Buscar si ya existe un attachment con el mismo nombre para evitar duplicados
                        existing_attachment = self.env["ir.attachment"].search(
                            [("name", "=", report_name), ("res_model", "=", "mail.message"), ("res_id", "=", 0)],
                            limit=1,
                        )

                        if existing_attachment:
                            attachment = existing_attachment
                        else:
                            report_content, _ = self.env["ir.actions.report"]._render(
                                report.report_name, withholding.ids
                            )
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

                    # Agregar adjunto usando el método más directo
                    # En mass_mail mode usar comandos (4, id), en comment mode usar IDs simples
                    if email_mode:
                        attachment_ids.append((4, attachment.id))
                    else:
                        attachment_ids.append(attachment.id)

                except Exception:
                    continue

            mail_values_all[payment.id]["attachment_ids"] = attachment_ids

        return mail_values_all
