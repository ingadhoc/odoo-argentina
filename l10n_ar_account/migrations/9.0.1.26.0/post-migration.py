# -*- coding: utf-8 -*-
from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    # fix de un error de migración que producia que no se setee esto al migrar
    for company in env['res.company'].search([]):
        invoices = env['account.invoice'].search([
            ('currency_id', '!=', company.currency_id.id),
            ('company_id', '=', company.id)])
        for inv in invoices:
            inv.currency_rate = inv.get_localization_invoice_vals().get(
                'currency_rate')
