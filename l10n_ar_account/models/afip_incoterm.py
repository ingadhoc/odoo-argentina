# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models
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
