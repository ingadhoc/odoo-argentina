from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, 'l10n_ar_account', 'migrations/12.0.1.2.0/mig_data.xml')
    ref = env.ref
    doc_types = ref('l10n_ar_account.dc_liq_uci_a') + ref('l10n_ar_account.dc_liq_uci_b') + \
        ref('l10n_ar_account.dc_liq_uci_c') + ref('l10n_ar_account.dc_nc_liq_uci_a') + \
        ref('l10n_ar_account.dc_nc_liq_uci_b') + ref('l10n_ar_account.dc_nd_liq_uci_a') + \
        ref('l10n_ar_account.dc_nd_liq_uci_b') + ref('l10n_ar_account.dc_nd_liq_uci_c') + \
        ref('l10n_ar_account.dc_nc_liq_uci_c') + ref('l10n_ar_account.dc_bs_no_reg') + \
        ref('l10n_ar_account.dc_fce_a_f') + ref('l10n_ar_account.dc_fce_a_nd') + \
        ref('l10n_ar_account.dc_fce_a_nc') + ref('l10n_ar_account.dc_fce_b_f') + \
        ref('l10n_ar_account.dc_fce_b_nd') + ref('l10n_ar_account.dc_fce_b_nc') + \
        ref('l10n_ar_account.dc_fce_c_f') + ref('l10n_ar_account.dc_fce_c_nd') + \
        ref('l10n_ar_account.dc_fce_c_nc') + ref('l10n_ar_account.dc_liq_s_a') + \
        ref('l10n_ar_account.dc_liq_s_b') + ref('l10n_ar_account.dc_oc_ncrg3419') + \
        ref('l10n_ar_account.dc_desp_imp') + ref('l10n_ar_account.dc_imp_serv') + \
        ref('l10n_ar_account.dc_a_o_rg1415') + ref('l10n_ar_account.dc_b_o_rg1415') + \
        ref('l10n_ar_account.dc_c_o_rg1415')
    env['account.move'].search([('document_type_id', 'in', doc_types.ids)])._compute_display_name()
