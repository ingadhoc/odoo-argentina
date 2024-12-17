{
    'name': 'Argentinian withholding UX',
    'version': "17.0.1.8.0",
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'l10n_ar_withholding',
        'account_payment_pro',
    ],
    'data': [
        'views/report_withholding_certificate_templates.xml',
        'views/report_payment_receipt_templates.xml',
        'views/account_payment.xml',
        'views/account_tax_view.xml',
        'views/l10n_ar_payment_withholding_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    # 'post_init_hook': 'post_init_hook',
    'post_load': 'monkey_patch_synchronize_to_moves',
}
