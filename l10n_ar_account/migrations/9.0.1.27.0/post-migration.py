from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    # fix de un error de migración que producia que no se setee esto al migrar
    for company in env['res.company'].search([]):
        # arreglamos facturas en otras monedas
        invoices = env['account.invoice'].search([
            ('currency_rate', '=', 0.0),
            ('currency_id', '!=', company.currency_id.id),
            ('company_id', '=', company.id),
            ('company_id.localization', '=', 'argentina')])
        for inv in invoices:
            inv.currency_rate = inv.get_localization_invoice_vals().get(
                'currency_rate')
        # arreglamos facturas en ars
        env['account.invoice'].search([
            ('currency_id', '=', company.currency_id.id),
            ('currency_rate', '=', 0.0),
            ('company_id', '=', company.id),
            ('company_id.localization', '=', 'argentina')]).write({
                'currency_rate': 1.0})
