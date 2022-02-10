from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute("""
        UPDATE account_journal SET l10n_ar_is_pos = FALSE, l10n_ar_afip_pos_system = Null
        WHERE account_journal.l10n_ar_afip_pos_system = 'not_applicable'""")
