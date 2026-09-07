from odoo import models


class AccountTax(models.Model):
    _inherit = "account.tax"

    def _l10n_ar_withholding_regime_key(self):
        """Clave de identidad del régimen, o False si el impuesto no es una retención.

        Dos registros de ``account.tax`` con la misma clave son el mismo régimen. Es lo
        que permite reconciliar los duplicados que dejó la migración de bases con
        sucursales: el régimen existía en la compañía padre y en la hija, y al unificar
        quedó uno activo y el otro archivado.

        No entran ni el nombre ni la alícuota (la migración pudo renombrar el impuesto y
        las alícuotas cambian con el tiempo) ni ``tax_group_id`` (los grupos también se
        unificaron, así que el duplicado archivado puede apuntar a otro registro).
        """
        self.ensure_one()
        if not self.l10n_ar_withholding_payment_type:
            return False
        return (
            self.company_id.root_id.id,
            self.l10n_ar_withholding_payment_type,
            self.l10n_ar_tax_type or False,
            self.l10n_ar_state_id.id,
            # normalizamos a False para que un código vacío ('') no difiera de uno sin cargar
            self.l10n_ar_code or False,
        )
