{
    'name': 'Argentinian withholding UX',
    'version': "17.0.0.0.0",
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
        'views/account_payment.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    # 'post_init_hook': 'post_init_hook',
    # 'post_load': 'monkey_patch_inverse_l10n_latam_document_number',
}
