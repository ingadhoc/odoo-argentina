# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields
import logging
_logger = logging.getLogger(__name__)


class afip_document_class(models.Model):
    _inherit = "afip.document_class"

    export_to_citi = fields.Boolean(
        help='Set True if this document type and can be imported on citi'
    )
