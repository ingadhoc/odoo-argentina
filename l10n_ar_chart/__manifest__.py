{
    'name': 'Argentina - Planes Contables',
    'author': 'Moldeo Interactive,ADHOC SA,Odoo Community Association (OCA)',
    'category': 'Localization/Account Charts',
    'license': 'AGPL-3',
    'depends': [
        # for afip_code on fiscal position and other tax modifications
        'l10n_ar_account',
        'account_withholding',
        'account_check',
    ],
    'data': [
        'data/account_group_data.xml',
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_data2.xml',

        'data/account_chart_template.xml',
        'data/account_tax_template.xml',
        'data/account_tax_withholding_template.xml',
        'data/account_fiscal_template.xml',
    ],
    'demo': [
        # MOVEMOS demo data a modulo custom para poder cargar otros datos demo
        # # para datos demo agregamos alicuotas a las percepciones aplicadas y
        # # sufridas
        # '../l10n_ar_account/demo/account_tax_template_demo.xml',
        # # TODO los productos se podrian cargar en l10n_ar_account
        # '../l10n_ar_account/demo/product_product_demo.xml',
        # '../l10n_ar_account/demo/account_tax_template_demo.xml',
        # # we add this file only fot tests run by odoo, we could use
        # # an yml testing if config.options['test_enable'] and only load it
        # # in that case
        # '../l10n_ar_account/demo/account_journal_demo.xml',
    ],
    'installable': True,
    'images': [
    ],
    'version': '12.0.1.0.0',
}
