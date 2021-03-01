from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute("""
        UPDATE res_partner SET start_date = rc.l10n_ar_afip_start_date
        FROM res_company as rc
        WHERE res_partner.id = rc.partner_id
            AND res_partner.start_date is null
            AND rc.l10n_ar_afip_start_date is not null""")
