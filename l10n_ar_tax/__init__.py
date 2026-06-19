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
        # When l10n_ar_withholding_line_ids triggers the sync, distinguish structural
        # changes (withholding taxes added or removed) from non-structural ones (e.g.
        # sequence name assignment in action_post via Command.update).
        #
        # Non-structural (tax sets on payment and move already match) → skip the sync
        # entirely; the core would try to delete withholding lines that already have
        # display_type='tax' (set by _recompute_tax_lines), causing
        # _prevent_automatic_line_deletion to raise even without dynamic_unlink.
        #
        # Structural (tax sets differ: line added or deleted) → apply dynamic_unlink=True
        # so withholding move lines with display_type='tax' can be safely replaced.
        ctx_self = self
        if "l10n_ar_withholding_line_ids" in changed_fields:
            needs_structural_sync = False
            for payment in self:
                active_wth_tax_ids = set(
                    t.id
                    for t in payment.l10n_ar_withholding_line_ids.mapped("tax_id")
                    if t.l10n_ar_withholding_sequence_id
                )
                existing_wth_move_tax_ids = set(
                    l.tax_line_id.id
                    for l in payment.move_id.line_ids
                    if l.tax_line_id and l.tax_line_id.l10n_ar_withholding_sequence_id
                )
                if active_wth_tax_ids != existing_wth_move_tax_ids:
                    needs_structural_sync = True
                    break
            if not needs_structural_sync:
                return
            ctx_self = self.with_context(dynamic_unlink=True)
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
