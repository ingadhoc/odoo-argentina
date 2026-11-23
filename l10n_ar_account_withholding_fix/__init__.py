##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    records = env['ir.model.data'].search([
        ('module', '=', 'l10n_ar_account_withholding_fix'),
        ('model', '=', 'account.tax'),
    ])
    records.write({
        'module': 'l10n_ar_account_withholding',
        'noupdate': True,
    })
    _logger.info(records.read([]))
