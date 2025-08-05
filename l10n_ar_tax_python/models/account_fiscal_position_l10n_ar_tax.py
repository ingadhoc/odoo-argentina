import logging

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class AccountFiscalPositionL10nArTax(models.Model):
    _inherit = "account.fiscal.position.l10n_ar_tax"

    webservice = fields.Selection(
        selection_add=[("python_formula", "Python Formula")],
    )
    python_formula = fields.Text(
        help="Python code to compute the tax amount.\n"
        "Available variables: partner, to_date, from_date, default_tax\n"
        "The code should return a variable named 'aliquot' "
        "Example: aliquot = 0.21 (for a tax of 21%)\n",
    )

    @api.constrains("webservice", "tax_type")
    def _check_python_formula(self):
        """Por ahora no permitimos usar webservice == 'python_formula' con tax_type != 'withholding' hasta validar necesidad"""
        for rec in self:
            if rec.webservice == "python_formula" and rec.tax_type != "withholding":
                raise ValidationError(
                    _(
                        "No se puede usar el webservice 'python_formula' con un tipo de impuesto diferente a 'withholding'."
                    )
                )

    def _get_missing_taxes(self, partner, date):
        python_formula = self.filtered(lambda x: x.webservice == "python_formula")
        taxes = super(AccountFiscalPositionL10nArTax, self - python_formula)._get_missing_taxes(partner, date)
        from_date = date + relativedelta(day=1)
        to_date = from_date + relativedelta(days=-1, months=+1)
        for rec in python_formula:
            local_dict = {
                "partner": partner,
                "to_date": to_date,
                "from_date": from_date,
                "default_tax": rec.default_tax_id,
            }
            safe_eval(
                self.python_formula,
                local_dict,
                mode="exec",
                nocopy=True,
            )
            aliquot = local_dict.get("aliquot", None)
            if aliquot:
                taxes |= self._ensure_tax(aliquot * 100)
        return taxes

    def action_edit_python_formula(self):
        """Abrir popup para editar la fórmula Python"""
        return {
            "name": _("Edit Python Formula"),
            "type": "ir.actions.act_window",
            "res_model": "account.fiscal.position.l10n_ar_tax",
            "res_id": self.id,
            "view_mode": "form",
            "view_id": self.env.ref("l10n_ar_tax_python.view_l10n_ar_tax_python_formula_form").id,
            "target": "new",
            "context": {"default_id": self.id},
        }

    def action_save_python_formula(self):
        """Guardar la fórmula Python y cerrar el popup"""
        return {"type": "ir.actions.act_window_close"}
