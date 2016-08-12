# -*- coding: utf-8 -*-
{
    "name": "Argentina - Web Services de Factura Electrónica del AFIP",
    'version': '9.0.0.0.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author':  'ADHOC SA, Moldeo Interactive',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'l10n_ar_afipws',
        # 'l10n_ar_account',
        # TODO improove this, we add this dependency because of demo data only
        # becuase demo data needs de chart account installed, we should
        # take this data tu l10n_ar_chart and set electronic if available
        'l10n_ar_chart',
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
        'data/afip.wsfe_error.csv',
        'security/ir.model.access.csv',
    ],
    'demo': [
        # 'demo/account_demo.xml',
        # 'demo/ri_sale_invoice_demo.xml',
        'demo/account_journal_demo.yml',
        'demo/account_invoice_demo.yml',
    ],
    'test': [
    ],
    'images': [
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
