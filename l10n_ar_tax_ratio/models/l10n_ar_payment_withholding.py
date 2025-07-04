from odoo import models


class l10nArPaymentWithholding(models.Model):
    _inherit = "l10n_ar.payment.withholding"

    def _compute_base_amount(self):
        super()._compute_base_amount()
        # esto lo hicimos así para soportar el caso de una posición fiscal que tenga más de un impuesto con ratio,
        # pero actualmente una misma posicion fiscal no puedo agregar 2 impuestos del mismo grupo (ej VAT Withholding)
        # Lo dejamos por el momento con la aclaración por si en un futuro sacamos la constraint de los grupos de impuestos.
        for wth in self.filtered(lambda x: x.tax_id.amount_type == "percent" and x.tax_id.ratio != 100):
            wth.base_amount *= wth.tax_id.ratio / 100
