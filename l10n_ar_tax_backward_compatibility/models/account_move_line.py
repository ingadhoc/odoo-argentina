import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_withholding(self):
        """Fallback de matching para pagos de bases migradas con sucursales.

        La migración unificó los impuestos de las compañías hijas en la compañía padre y
        archivó los duplicados: el apunte contable quedó apuntando al impuesto
        superviviente y la línea de retención del pago al duplicado archivado, con lo cual
        el match por identidad de registro del compute de ``l10n_ar_tax`` no encuentra
        nada. Cuando falla, buscamos la retención por identidad de régimen. El caso y las
        guardas están documentados en el README.
        """
        super()._compute_withholding()
        todo = self.filtered(lambda x: not x.withholding_id and x.tax_line_id and x.payment_id)
        if not todo:
            return

        regime_keys = {}  # tax.id -> clave de régimen, memo del batch del compute

        def regime_key(tax):
            if tax.id not in regime_keys:
                regime_keys[tax.id] = tax._l10n_ar_withholding_regime_key()
            return regime_keys[tax.id]

        for rec in todo:
            tax = rec.tax_line_id
            key = regime_key(tax)
            if not key:
                continue
            # Solo reconciliamos data migrada (alguno de los dos impuestos archivado) y
            # solo si no hay ambigüedad: un pago nuevo mal armado tiene que seguir
            # fallando de forma visible en vez de resolverse por adivinanza.
            candidates = rec.payment_id.l10n_ar_withholding_line_ids.filtered(
                lambda x: not (x.tax_id.active and tax.active) and regime_key(x.tax_id) == key
            )
            if len(candidates) == 1:
                rec.withholding_id = candidates
            elif candidates:
                _logger.warning(
                    "No se pudo resolver la retención del apunte %s: %s líneas del pago %s comparten el "
                    "régimen del impuesto %s.",
                    rec.id,
                    len(candidates),
                    rec.payment_id.id,
                    tax.id,
                )
