# -*- coding: utf-8 -*-
from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    # los hacemos actualizables a partir de esta version
    env['ir.model.data'].search([
        ('module', '=', 'l10n_ar_account', ),
        ('name', 'in', ['validator_numero_factura', 'validator_despacho'])],
    ).write({'noupdate': False})
    openupgrade.load_data(
        env.cr, 'l10n_ar_account', 'data/base_validator_data.xml')
