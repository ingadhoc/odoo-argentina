import datetime
import logging

from odoo import api, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class L10nArPartnerTax(models.Model):
    _inherit = "l10n_ar.partner.tax"

    @api.constrains("partner_id", "tax_id", "from_date", "to_date")
    def _check_tax_group_overlap(self):
        for record in self:
            domain = [
                ("id", "!=", record.id),
                ("partner_id", "=", record.partner_id.id),
                ("tax_id.tax_group_id", "=", record.tax_id.tax_group_id.id),
                "&",
                "|",
                ("from_date", "=", False),
                ("from_date", "<=", record.to_date or datetime.date.max),
                "|",
                ("to_date", "=", False),
                ("to_date", ">=", record.from_date or datetime.date.min),
                # only companies that can see both lines (same ancestry chain) can conflict
                "|",
                ("company_id", "parent_of", record.company_id.id),
                ("company_id", "child_of", record.company_id.id),
            ]
            if record.tax_id.l10n_ar_withholding_payment_type == "supplier":
                # TODO esto lo deberiamos borrar al ir a odoo 19 y solo usar los tax groups
                # por ahora, para no renegar con scripts de migra que requieran crear tax groups para cada jurisdiccion y
                # ademas luego tener que ajustar a lo que hagamos en 19, usamos la jursdiccion como elemento de agrupacion
                # solo para retenciones
                domain += [("tax_id.l10n_ar_state_id", "=", record.tax_id.l10n_ar_state_id.id)]
            conflicting_records = self.search(domain)
            if conflicting_records:
                raise ValidationError(
                    "No puede haber dos impuestos del mismo grupo vigentes en el mismo momento para la misma empresa. "
                    "Tal vez tenga algun impuesto al que le tenga que definir una fecha hasta. Más información:\n"
                    "* Impuesto: %s\n"
                    "* Fecha Hasta: %s\n"
                    "* Fecha Desde: %s\n"
                    "* Otros impuestos: %s\n"
                    % (
                        record.tax_id.name,
                        record.to_date,
                        record.from_date,
                        ["%s (%s)" % (line.tax_id.name, line.company_id.name) for line in conflicting_records],
                    )
                )
