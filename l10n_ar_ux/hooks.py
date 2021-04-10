##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


def set_tax_included(cr, registry):
    _logger.info('Settig tax included by default')
    env = api.Environment(cr, SUPERUSER_ID, {'active_test': False})
    # if this option was never configured we set it as tax_included. This is useful for ecommerce
    # where in argentina normally ecommerce are b2c. account_ux and sale_ux areadly modify the backend
    # so that this does not affect backend users.
    if not env.ref('account.show_line_subtotals_tax_selection', False):
        env['ir.config_parameter'].set_param('account.show_line_subtotals_tax_selection', 'tax_included')
        for groupId in ['base.group_portal', 'base.group_user', 'base.group_public']:
            group = env.ref(groupId, False)
            if not group:
                continue
            group.write({'implied_ids': [(3, env.ref('account.group_show_line_subtotals_tax_excluded').id)]})
            env.ref('account.group_show_line_subtotals_tax_excluded').write({'users': [(5,)]})

            group.write({'implied_ids': [(4, env.ref('account.group_show_line_subtotals_tax_included').id)]})


def post_init_hook(cr, registry):
    """Loaded after installing the module """
    _logger.info('Post init hook initialized')
    set_tax_included(cr, registry)
