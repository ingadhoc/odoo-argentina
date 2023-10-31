{
    'name': 'Argentinian withholding UX',
    'version': "16.5.0.0.0",
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'l10n_ar_withholding',
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
