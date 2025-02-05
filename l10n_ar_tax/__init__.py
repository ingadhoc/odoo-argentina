##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from . import wizard
from odoo.addons.l10n_ar_withholding.models.account_payment import AccountPayment
import logging

_logger = logging.getLogger(__name__)


def monkey_patch_synchronize_to_moves():
    def _synchronize_to_moves(self, changed_fields):
        return super(AccountPayment, self)._synchronize_to_moves(changed_fields)

    AccountPayment._synchronize_to_moves = _synchronize_to_moves


def _l10n_ar_update_taxes(env):
    """Al instalar este módulo, en caso de que existan compañías responsable inscripto argentinas y con plan de cuentas
    ajustamos ciertos datos de los impuestos
    TODO la mayoria de esto deberia implementarse en odoo standard
    """

    # si tiene instalado chart ri o exento le actualizamos impuestos
    companies = env["res.company"].search([("chart_template", "in", ("ar_base", "ar_ri", "ar_ex"))])
    for company in companies:
        env["account.chart.template"]._add_wh_taxes(company)

    # Dejamos registro en los logs de las compañías en las cuales se estableció el código de impuesto
    if companies:
        _logger.info(
            "Se agregaron los códigos de impuestos correspondientes para retenciones de ganancias aplicadas y retenciones de iva aplicadas y las etiquetas de impuestos para compañías %s."
            % ", ".join(companies.mapped("name"))
        )
