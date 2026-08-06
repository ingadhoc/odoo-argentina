from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _get_withholding_certificates_report(self):
        return self.env.ref(
            "l10n_ar_tax.action_report_withholding_certificate",
            raise_if_not_found=False,
        )

    def _compute_attachment_ids(self):
        """Extends original method so it is possible to attach and preview a
        single PDF holding all the withholding certificates (one page per
        withholding) when sending payment reports by email.
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

            report = composer._get_withholding_certificates_report()
            if not report:
                continue

            payment = self.env["account.payment"].browse(res_ids)
            if payment.partner_type != "supplier":
                continue

            withholdings = payment.l10n_ar_withholding_line_ids.filtered("amount")
            if not withholdings:
                continue

            report_name = payment._l10n_ar_withholding_certificates_filename()

            # El compute puede correr varias veces mientras el usuario edita el
            # wizard: si ya renderizamos el PDF para este composer, reusarlo en
            # vez de volver a renderizar y crear otro adjunto temporal.
            attachment = self.env["ir.attachment"].search(
                [
                    ("name", "=", report_name),
                    ("res_model", "=", "mail.compose.message"),
                    ("res_id", "=", composer.id),
                ],
                limit=1,
            )
            if not attachment:
                # Un solo _render con todas las retenciones: el template itera
                # sobre docs, así que esto devuelve un único PDF de N páginas
                # (una corrida de wkhtmltopdf en vez de una por retención).
                report_content, _content_type = self.env["ir.actions.report"]._render(
                    report.report_name, withholdings.ids
                )
                # Crear adjunto temporal para previsualización
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": report_name,
                        "raw": report_content,
                        "mimetype": "application/pdf",
                        "res_model": "mail.compose.message",
                        "res_id": composer.id,
                        "type": "binary",
                    }
                )

            if attachment.id not in composer.attachment_ids.ids:
                composer.attachment_ids = [(4, attachment.id)]

    def _prepare_mail_values(self, res_ids):
        """Extended to attach a single PDF with all the withholding
        certificates when sending payments by email in rendering mode (mass
        mail or comment in batch), where the preview compute does not run.

        In monorecord "rendered" mode there is nothing to do here: the PDF
        rendered by _compute_attachment_ids is part of attachment_ids and
        _prepare_mail_values_rendered already carries it to the message."""
        mail_values_all = super()._prepare_mail_values(res_ids)

        rendering_mode = self.composition_mode == "mass_mail" or self.composition_batch
        if self.model != "account.payment" or not rendering_mode:
            return mail_values_all

        report = self._get_withholding_certificates_report()
        if not report:
            return mail_values_all

        # En mass_mail mode los attachments van como comandos (4, id), en comment mode como IDs simples
        email_mode = self.composition_mode == "mass_mail"

        payments = self.env["account.payment"].browse(res_ids).filtered(lambda p: p.partner_type == "supplier")
        for payment in payments:
            if payment.id not in mail_values_all:
                continue

            withholdings = payment.l10n_ar_withholding_line_ids.filtered("amount")
            if not withholdings:
                continue

            # Un solo render con todas las retenciones del pago. Gracias a
            # attachment_use en el reporte, los certificados ya renderizados se
            # recargan de su attachment cacheado en vez de volver a pasar por
            # wkhtmltopdf.
            report_content, _content_type = self.env["ir.actions.report"]._render(report.report_name, withholdings.ids)
            attachment = self.env["ir.attachment"].create(
                {
                    "name": payment._l10n_ar_withholding_certificates_filename(),
                    "raw": report_content,
                    "mimetype": "application/pdf",
                    "res_model": "mail.message",
                    "res_id": 0,
                    "type": "binary",
                }
            )

            attachment_ids = mail_values_all[payment.id].get("attachment_ids") or []
            if email_mode:
                attachment_ids.append((4, attachment.id))
            else:
                attachment_ids.append(attachment.id)
            mail_values_all[payment.id]["attachment_ids"] = attachment_ids

        return mail_values_all
