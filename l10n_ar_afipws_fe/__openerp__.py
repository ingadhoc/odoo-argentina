# -*- coding: utf-8 -*-
{
    "name": "Factura Electrónica Argentina",
    'version': '9.0.1.0.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA, Moldeo Interactive',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'l10n_ar_afipws',
        'l10n_ar_account',
    ],
    'external_dependencies': {
    },
    'data': [
        'wizard/afip_ws_consult_wizard_view.xml',
        'wizard/afip_ws_currency_rate_wizard_view.xml',
        'views/invoice_view.xml',
        'views/account_journal_document_type_view.xml',
        'views/wsfe_error_view.xml',
        'views/account_journal_view.xml',
        'views/product_uom_view.xml',
        'views/res_currency_view.xml',
        'res_config_view.xml',
        'views/res_company_view.xml',
        'data/afip.wsfe_error.csv',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'test': [
    ],
    'images': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
