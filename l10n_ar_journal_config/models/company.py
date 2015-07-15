# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class res_company(models.Model):
    _inherit = "res.company"

    point_of_sale_ids = fields.One2many(
        'afip.point_of_sale',
        'company_id',
        'AFIP Point of Sales',
        )
    journal_ids = fields.One2many(
        'account.journal',
        'company_id',
        'Journals'
        )
