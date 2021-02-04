##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    group_include_pending_receivable_documents = fields.Boolean(
        string="Mostrar comprobantes pendientes en Recibos de Clientes",
        implied_group='l10n_ar_ux.group_include_pending_receivable_documents',
        help="Si marca esta opción, cuando se imprima o envíe un Recibo de Clientes, se incluirá"
        " una sección con todos los Comprobantes abiertos, es decir, que tengan algún saldo pendiente")
