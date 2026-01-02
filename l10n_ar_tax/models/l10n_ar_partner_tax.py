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
            ]
            conflicting_records = self.search(domain)
            if conflicting_records:
                raise ValidationError(
                    "No puede haber dos impuestos del mismo grupo vigentes en el mismo momento para la misma empresa. "
                    "Tal vez tenga algun impuesto al que le tenga que definir una fecha hasta. Más información:\n"
                    "* Impuesto: %s\n"
                    "* Fecha Hasta: %s\n"
                    "* Fecha Desde: %s\n"
                    "* Otros impuestos: %s\n"
                    % (record.tax_id.name, record.to_date, record.from_date, conflicting_records.mapped("tax_id.name"))
                )
