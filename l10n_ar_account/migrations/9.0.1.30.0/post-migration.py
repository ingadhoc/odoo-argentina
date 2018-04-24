# -*- coding: utf-8 -*-
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(cr, version):
    openupgrade.load_data(
        cr, 'l10n_ar_account',
        'migrations/9.0.1.30.0/account.document.type.csv')
