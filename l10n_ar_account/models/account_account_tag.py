# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class AccountAccountTag(models.Model):

    _inherit = 'account.account.tag'

    jurisdiction_code = fields.Char(
        size=3,
    )
    # por si queremos vincular los tags con las provincias
    # state_id = fields.Many2one(
    #     '',
    # )
