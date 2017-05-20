# -*- coding: utf-8 -*-
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(cr, version):
    """
    unificamos el modulo de padron en l10n_ar_account
    """
    openupgrade.update_module_names(
        cr, [('l10n_ar_padron_afip', 'l10n_ar_account')],
        merge_modules=True,)
