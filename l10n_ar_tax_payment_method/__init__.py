##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models


def _l10n_ar_set_apply_withholding(env):
    """Al instalar el módulo, dejamos activo el cálculo de retenciones en TODOS los
    métodos de pago salientes existentes (el default del campo ya lo hace para los nuevos)."""
    lines = env["account.payment.method.line"].search([("payment_type", "=", "outbound")])
    lines.l10n_ar_apply_withholding = True
