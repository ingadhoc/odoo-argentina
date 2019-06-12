from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, 'l10n_ar_account_vat_ledger',
        'migrations/11.0.11.0.0/mig_data.xml')
