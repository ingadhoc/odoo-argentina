from odoo import fields, models


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    # en l10n_ar_withholding se esta creando el tax group "VAT withholding" con este código. Nos viene bien para que
    # en l10n_ar_account_reports podamos filtrar los impuestos de IVA retenidos o percibidos si bien formalmente
    # para arca probablemente debería ser otro código. Igual estos códigos se usan solo para WS
    l10n_ar_tribute_afip_code = fields.Selection(
        selection_add=[
            ("06", "06 - VAT perception or Withholding"),
        ]
    )
    l10n_ar_state_id = fields.Many2one(
        "res.country.state", string="Jurisdiction", ondelete="restrict", domain="[('country_id', '=?', country_id)]"
    )
    l10n_ar_withholding_sequence_id = fields.Many2one(
        "ir.sequence",
        string="WTH Sequence",
        copy=True,  # mejora de usabilidad, duplicar un tax group mantiene la secuencia
        check_company=True,
        help="If no sequence provided then it will be required for you to enter withholding number when registering one.",
    )
