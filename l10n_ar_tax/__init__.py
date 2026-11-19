##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from . import wizard
from . import demo
import logging

_logger = logging.getLogger(__name__)


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

    # _auto_init skipped the fiscal position compute over the whole payment history: draft supplier
    # payments are the only ones that would get a value, so we compute just those (and, through
    # them, their withholding lines)
    payments = env["account.payment"].search([("state", "=", "draft"), ("partner_type", "=", "supplier")])
    env.add_to_compute(payments._fields["l10n_ar_fiscal_position_id"], payments)
