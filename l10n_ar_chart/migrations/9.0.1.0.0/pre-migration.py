# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade
from odoo import SUPERUSER_ID
from odoo.modules.registry import RegistryManager


def uninstall_depreceated_chart_modules(cr):
    pool = RegistryManager.get(cr.dbname)
    ir_module_module = pool['ir.module.module']
    domain = [('name', 'in', [
        'l10n_ar_chart_generic_tax_settlement',
        'l10n_ar_chart_generic_withholding']),
        ('state', 'in', ('installed', 'to install', 'to upgrade'))]
    ids = ir_module_module.search(cr, SUPERUSER_ID, domain)
    ir_module_module.module_uninstall(cr, SUPERUSER_ID, ids)
    ir_module_module.unlink(cr, SUPERUSER_ID, ids)


@openupgrade.migrate()
def migrate(cr, version):
    uninstall_depreceated_chart_modules(cr)

    # dont know why but some witholding templates could remain and give an
    # error
    if openupgrade.table_exists(cr, 'account_tax_withholding_template'):
        openupgrade.logged_query(cr, """
            DELETE from account_tax_withholding_template
            """)

    # remove taxes that gives an error because of duplicated name
    openupgrade.logged_query(cr, """
        DELETE from account_tax_template tb
        using ir_model_data d where tb.id=d.res_id
        and d.model = 'account.tax.template'
        and d.module = 'l10n_ar_chart'
        """)
