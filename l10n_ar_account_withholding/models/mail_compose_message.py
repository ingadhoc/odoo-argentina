from odoo import models
from odoo.tools import safe_eval
import base64


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

<<<<<<< 3b184eceedfd74f4a3787eb07f4ddbb3a579bff1
    def _compute_attachment_ids(self):
        """ Extendemos el método original para que se pueda previsualizar en el envío de mails de pagos el/los archivos de retenciones. """
        super()._compute_attachment_ids()
        for composer in self:
            res_ids = composer._evaluate_res_ids() or [0]
            if composer.model == 'account.payment' and composer.template_id and len(res_ids) == 1:
                payment = self.env[composer.model].browse(res_ids)
                if payment.partner_type != 'supplier':
                    return
||||||| dc114988f1ebcc7c7aea8674d0d68472e0e82f94
    def _onchange_template_id(self, template_id, composition_mode, model, res_id):
        values = super()._onchange_template_id(
            template_id, composition_mode, model, res_id)
        if template_id and model == 'account.payment.group':
            payment_group = self.env[model].browse(res_id)
            if payment_group.partner_type != 'supplier':
                return values
            report = self.env.ref('l10n_ar_account_withholding.action_report_withholding_certificate', raise_if_not_found=False)
            if not report:
                return values
            attachment_ids = []
            for payment in payment_group.payment_ids.filtered(lambda p: p.payment_method_code == 'withholding'):
                report_name = safe_eval.safe_eval(report.print_report_name, {'object': payment})
                result, format = self.env['ir.actions.report']._render(report.report_name, payment.ids)
                file = base64.b64encode(result)
                data_attach = {
                    'name': report_name,
                    'datas': file,
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',
                }
                attachment_ids.append(self.env['ir.attachment'].create(data_attach).id)
            if values.get('value', False) and values['value'].get('attachment_ids', []) or attachment_ids:
                values_attachment_ids = values['value'].get('attachment_ids', False) and values['value']['attachment_ids'][0][2] or []
                values['value']['attachment_ids'] = [(6, 0, values_attachment_ids + attachment_ids)]
=======
    def _onchange_template_id(self, template_id, composition_mode, model, res_id):
        values = super()._onchange_template_id(
            template_id, composition_mode, model, res_id)
        if template_id and model == 'account.payment.group':
            payment_group = self.env[model].browse(res_id)
            if payment_group.partner_type != 'supplier':
                return values
            report = self.env.ref('l10n_ar_account_withholding.action_report_withholding_certificate', raise_if_not_found=False)
            if not report:
                return values
            attachment_ids = []
            for payment in payment_group.payment_ids.filtered(lambda p: p.payment_method_code == 'withholding'):
                report_name = safe_eval.safe_eval(report.print_report_name, {'object': payment})
                result, format = self.env['ir.actions.report']._render(report.report_name, payment.ids)
                file = base64.b64encode(result)
                data_attach = {
                    'name': "%s.%s" % (report_name, format),
                    'datas': file,
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',
                    'mimetype': 'application/pdf',
                }
                attachment_ids.append(self.env['ir.attachment'].create(data_attach).id)
            if values.get('value', False) and values['value'].get('attachment_ids', []) or attachment_ids:
                values_attachment_ids = values['value'].get('attachment_ids', False) and values['value']['attachment_ids'][0][2] or []
                values['value']['attachment_ids'] = [(6, 0, values_attachment_ids + attachment_ids)]
>>>>>>> 1f55ff0f716a3459ea5c7098ddc2cea7d18c6bfc

                report = self.env.ref('l10n_ar_withholding_ux.action_report_withholding_certificate', 
                                      raise_if_not_found=False)
                if not report:
                    return
                for withholding in payment.l10n_ar_withholding_line_ids:
                    report_name = safe_eval.safe_eval(report.print_report_name, {'object': withholding})
                    result, _ = self.env['ir.actions.report']._render(report.report_name, withholding.ids)
                    file = base64.b64encode(result)
                    data_attach = {
                        'name': report_name,
                        'datas': file,
                        'res_model': 'mail.compose.message',
                        'res_id': 0,
                        'type': 'binary',
                    }
                    composer.attachment_ids += self.env['ir.attachment'].create(data_attach)
