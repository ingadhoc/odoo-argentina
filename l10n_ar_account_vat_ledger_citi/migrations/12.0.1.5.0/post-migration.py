from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, 'l10n_ar_account_vat_ledger_citi',
        'migrations/12.0.1.5.0/mig_data.xml')
