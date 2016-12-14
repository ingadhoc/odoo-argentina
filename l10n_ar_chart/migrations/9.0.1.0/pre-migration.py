# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(cr, version):
    # remove taxes that gives an error because of duplicated name
    openupgrade.logged_query(cr, """
        DELETE from account_tax_template tb
        using ir_model_data d where tb.id=d.res_id
        and d.model = 'account.tax.template'
        and d.module = 'l10n_ar_chart'
        """)
