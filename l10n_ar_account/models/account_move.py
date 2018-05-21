##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # lo agregamos en los moves y no en los lines porque en el codigo de odoo
    # parece decir que van a mover partner_id e invoice_id a los moves
    # y la verdad no se nos ocurre un caso donde se mesclen partners, de hecho
    # solo interesa si el move tiene partner (no se mezcla), no interesa
    # para move lines de deuda o asientos de inicio, etc
    # seteamos este campo aca ya que por mas que cambie el partner necesitamos
    # que este dato sea fijo y no cambie
    afip_responsability_type_id = fields.Many2one(
        'afip.responsability.type',
        string='AFIP Responsability Type',
        readonly=True,
        copy=False,
        auto_join=True,
    )

    @api.multi
    @api.constrains('partner_id')
    def set_afip_responsability_type_id(self):
        for rec in self:
            commercial_partner = rec.partner_id.commercial_partner_id
            rec.afip_responsability_type_id = (
                commercial_partner.afip_responsability_type_id.id)
