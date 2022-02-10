##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    l10n_ar_copies = fields.Selection(
        selection=[
            # ('original', 'Solo Original'),
            ('duplicado', 'Duplicado'), ('triplicado', 'Duplicado y Triplicado')],
        string="Agregar Duplicado/Triplicado",)

    @api.model
    def _get_rendering_context(self, docids, data):
        res = super()._get_rendering_context(docids, data)
        l10n_ar_copies = ['']
        is_email = 'force_email' in self._context or 'default_subject' in self._context
        if not is_email and self.l10n_ar_copies:
            l10n_ar_copies = ['ORIGINAL', 'DUPLICADO']
            if self.l10n_ar_copies == 'triplicado':
                l10n_ar_copies += ['TRIPLICADO']
        res.update({
            'l10n_ar_copies_list': l10n_ar_copies,
        })
        return res
