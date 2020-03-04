##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


def document_types_not_updatable(cr, registry):
    _logger.info('Update l10n_latam.document.type to noupdate=True')
    env = api.Environment(cr, SUPERUSER_ID, {})
    items = env['ir.model.data'].search([
        ('model', '=', 'l10n_latam.document.type'),
        ('module', '=', 'l10n_ar'),
    ])
    items = items.write({'noupdate': True})


def post_init_hook(cr, registry):
    """Loaded after installing the module """
    _logger.info('Post init hook initialized')
    document_types_not_updatable(cr, registry)
