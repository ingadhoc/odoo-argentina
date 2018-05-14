##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)


class AccountDocumentType(models.Model):
    _inherit = "account.document.type"

    export_to_citi = fields.Boolean(
        help='Set True if this document type and can be imported on citi'
    )
