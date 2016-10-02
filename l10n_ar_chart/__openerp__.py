# -*- coding: utf-8 -*-
{
    'name': 'Argentina - Planes Contables',
    'author': 'Moldeo Interactive,ADHOC SA',
    'category': 'Localization/Account Charts',
    'license': 'AGPL-3',
    'depends': [
        # for afip_code on fiscal position and other tax modifications
        'l10n_ar_account',
    ],
    'test': [],
    'data': [
        'data/account_chart_template.xml',
        'data/account_chart_respinsc.xml',
        'data/account_tax_template.xml',
        'data/account_fiscal_template.xml',
        'data/account_chart_template.yml',
        'data/menuitem.xml',
    ],
    'demo': [
        '../l10n_ar_account/demo/product_product_demo.xml',
        '../l10n_ar_account/demo/account_customer_invoice_demo.yml',
        '../l10n_ar_account/demo/account_supplier_invoice_demo.yml',
        '../account/demo/account_bank_statement.yml',
        # '../account/demo/account_invoice_demo.yml',
        # '../l10n_ar_account/demo/account_supplier_invoice_demo.yml',
        # '../l10n_ar_account/demo/account_supplier_invoice_demo.yml',
        # '../account/demo/account_invoice_demo.yml',
        # '../l10n_ar_account/demo/account_invoice_demo.yml',
    ],
    'installable': True,
    'images': [
    ],
    'version': '9.0.1.0.0',
}
