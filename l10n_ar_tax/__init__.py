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
        # dynamic_unlink=True allows deletion of withholding move lines (display_type='tax')
        # that _seek_for_lines classifies as write-off lines. Without it,
        # _prevent_automatic_line_deletion raises a ValidationError even in draft state.
        #
        # We only apply it when withholding move lines are actually being deleted: i.e., the
        # move still has a tax_line_id for a withholding tax that no longer exists in
        # l10n_ar_withholding_line_ids (orphaned line). This avoids a regression where
        # action_post triggers _synchronize_to_moves via Command.update (name-only change)
        # and dynamic_unlink=True would allow the move to be fully rebuilt prematurely.
        ctx_self = self
        if "l10n_ar_withholding_line_ids" in changed_fields:
            for payment in self:
                active_wth_tax_ids = payment.l10n_ar_withholding_line_ids.mapped("tax_id").ids
                has_orphan = any(
                    l.tax_line_id.l10n_ar_withholding_sequence_id
                    and l.tax_line_id.id not in active_wth_tax_ids
                    for l in payment.move_id.line_ids
                    if l.tax_line_id
                )
                if has_orphan:
                    ctx_self = self.with_context(dynamic_unlink=True)
                    break
        return super(AccountPayment, ctx_self)._synchronize_to_moves(changed_fields)

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
