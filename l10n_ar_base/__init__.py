# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import SUPERUSER_ID

from openerp.addons import account
old_auto_install_l10n = account._auto_install_l10n


def ar_auto_install_l10n(cr, registry):
    """
    overwrite of this function to install our localization module
    """
    country_code = registry['res.users'].browse(
        cr, SUPERUSER_ID, SUPERUSER_ID, {}).company_id.country_id.code
    if country_code and country_code == 'AR':
        module_ids = registry['ir.module.module'].search(
            cr, SUPERUSER_ID, [
                ('name', '=', 'l10n_ar_chart'),
                ('state', '=', 'uninstalled')])
        registry['ir.module.module'].button_install(
            cr, SUPERUSER_ID, module_ids, {})
    else:
        return old_auto_install_l10n(cr, registry)


account._auto_install_l10n = ar_auto_install_l10n
