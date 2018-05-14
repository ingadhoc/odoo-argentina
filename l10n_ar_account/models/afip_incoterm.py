##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models
import logging
_logger = logging.getLogger(__name__)


class AfipIncoterm(models.Model):
    _name = 'afip.incoterm'
    _description = 'Afip Incoterm'

    afip_code = fields.Char(
        'Code',
        required=True
    )
    name = fields.Char(
        'Name',
        required=True
    )
