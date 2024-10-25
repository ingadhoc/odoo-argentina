from odoo import models, fields


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    tax_ws_ids = fields.One2many('res.company.tax.ws', 'fiscal_position_id')

    def _l10n_ar_add_taxes(self, partner, company, date, tax_type):
        self.ensure_one()
        tax_ws = self.tax_ws_ids.filtered(lambda x: x.tax_type == tax_type)
        domain = self.env['l10n_ar.partner.tax']._check_company_domain(company)
        domain += [('tax_id.tax_group_id', 'in', tax_ws.mapped('default_tax_id.tax_group_id').ids)]
        domain += [
            '|', ('from_date', '<=', date), ('from_date', '=', False),
            '|', ('to_date', '>=', date), ('to_date', '=', False),
        ]
        if tax_type == 'perception':
            taxes = partner.l10n_ar_partner_perception_ids.filtered_domain(domain).mapped('tax_id')
        elif tax_type == 'withholding':
            taxes = partner.l10n_ar_partner_tax_ids.filtered_domain(domain).mapped('tax_id')

        # agregamos taxes para grupos de impuestos que no estaban seteados en el partner
        taxes += tax_ws.filtered(lambda x: x.default_tax_id.tax_group_id.id not in taxes.tax_group_id.ids)._get_missing_taxes(partner, date)
        return taxes
