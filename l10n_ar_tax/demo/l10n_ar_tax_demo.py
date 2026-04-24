from datetime import timedelta

from odoo import Command, api, fields, models


# pylint: disable=consider-merging-classes-inherited
class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _install_l10n_ar_tax_demo(self, companies):
        """Crea data demo de cheques para argentina"""
        # Usamos este módulo porque es el único que tiene dependencias de l10n_ar y l10n_latam_check
        for company in companies.filtered(lambda x: x.country_code == "AR"):
            self = self.with_company(company)
            today_dt = fields.Date.today()

            # Ingreso de Cheques de Terceros: Recibo de cliente con 3 cheques a 30, 60 y 90 días
            partner_cliente = self.env.ref("l10n_ar.res_partner_adhoc")
            journal_recibo = self.env.ref(f"account.{company.id}_third_party_check", raise_if_not_found=False)
            payment_method_in_third = (
                self.env["account.payment.method.line"].search(
                    [("code", "=", "new_third_party_checks"), ("journal_id", "=", journal_recibo.id)], limit=1
                )
                if journal_recibo
                else self.env["account.payment.method.line"]
            )
            cheques_terceros = [
                Command.create(
                    {
                        "name": "100031",
                        "payment_date": today_dt + timedelta(days=30),
                        "amount": 10000,
                        "bank_id": self.env["res.bank"].search([], limit=1).id,
                        "payment_method_line_id": payment_method_in_third.id,
                    }
                ),
                Command.create(
                    {
                        "name": "100061",
                        "payment_date": today_dt + timedelta(days=60),
                        "amount": 20000,
                        "bank_id": self.env["res.bank"].search([], limit=1).id,
                        "payment_method_line_id": payment_method_in_third.id,
                    }
                ),
                Command.create(
                    {
                        "name": "100091",
                        "payment_date": today_dt + timedelta(days=90),
                        "amount": 30000,
                        "bank_id": self.env["res.bank"].search([], limit=1).id,
                        "payment_method_line_id": payment_method_in_third.id,
                    }
                ),
            ]
            if journal_recibo and payment_method_in_third:
                recibo = self.env["account.payment"].create(
                    {
                        "payment_type": "inbound",
                        "partner_type": "customer",
                        "partner_id": partner_cliente.id,
                        "amount": 60000,
                        "journal_id": journal_recibo.id,
                        "payment_method_line_id": payment_method_in_third.id,
                        "l10n_latam_new_check_ids": cheques_terceros,
                        "to_pay_move_line_ids": [Command.clear()],
                        "company_id": company.id,
                    }
                )
                if recibo.state == "draft":
                    recibo.action_post()

            # Pago con cheque propio
            partner_proveedor = self.env.ref("l10n_ar.partner_afip")
            journal_pago = self.env["account.journal"].search(
                [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
            )
            payment_method_own = self.env["account.payment.method.line"].search(
                [("code", "=", "own_checks"), ("journal_id", "=", journal_pago.id)], limit=1
            )
            cheque_propio = [
                Command.create(
                    {
                        "name": "200003",
                        "payment_date": today_dt + timedelta(days=7),
                        "amount": 15000,
                        "bank_id": self.env["res.bank"].search([], limit=1).id,
                        "payment_method_line_id": payment_method_own.id,
                    }
                )
            ]
            if journal_pago and payment_method_own:
                pago = self.env["account.payment"].create(
                    {
                        "payment_type": "outbound",
                        "partner_type": "supplier",
                        "partner_id": partner_proveedor.id,
                        "amount": 15000,
                        "journal_id": journal_pago.id,
                        "payment_method_line_id": payment_method_own.id,
                        "l10n_latam_new_check_ids": cheque_propio,
                        "to_pay_move_line_ids": [Command.clear()],
                        "company_id": company.id,
                    }
                )
                if pago.state == "draft":
                    pago.action_post()
