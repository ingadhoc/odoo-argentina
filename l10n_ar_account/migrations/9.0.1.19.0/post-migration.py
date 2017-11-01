# -*- coding: utf-8 -*-
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(cr, version):
    # los hacemos no actualizables a partir de esta version
    cr.execute("""
        UPDATE ir_model_data set noupdate=True
        WHERE model = 'account.document.type' and module = 'l10n_ar_account'
    """)
