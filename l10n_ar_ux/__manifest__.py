{
    'name': 'Argentinian Accounting UX',
<<<<<<< HEAD
    'version': "17.0.1.0.0",
||||||| parent of 5a6a9f9b (temp)
    'version': "16.0.1.9.0",
=======
    'version': "16.0.1.10.0",
>>>>>>> 5a6a9f9b (temp)
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'l10n_ar',
        # 'l10n_ar_withholding',
        'l10n_latam_check',
        'account_ux',
    ],
    'data': [
        'data/res_currency_data.xml',
        'data/account_account_tag_data.xml',
        'wizards/account_move_change_rate_views.xml',
        'views/portal_templates.xml',
        'views/account_move_view.xml',
        'views/res_partner_view.xml',
        'views/afip_concept_view.xml',
        'views/afip_activity_view.xml',
        'views/afip_tax_view.xml',
        'views/report_invoice.xml',
        'reports/report_account_transfer.xml',
        'views/account_payment_view.xml',
        'views/account_journal_views.xml',
        'views/ir_actions_views.xml',
        # 'wizards/res_config_settings_views.xml',
        'reports/account_invoice_report_view.xml',
        'security/ir.model.access.csv',
        'security/l10n_ar_ux_security.xml',
        'data/res_groups_data.xml',
        'views/account_fiscal_position_view.xml'
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
    'post_init_hook': 'post_init_hook',
    'post_load': 'monkey_patches',
}
