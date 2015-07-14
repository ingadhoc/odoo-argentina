# -*- coding: utf-8 -*-
{
    'name': 'Retenciones para Plan Contable General Argentino',
    'author':  'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'version': '8.0.1',
    'category': 'Argentinian Localization',
    'sequence': 14,
    'summary': '',
    'license': 'AGPL-3',
    'description': """
Retenciones para Plan Contable General Argentino
================================================
""",
    'depends': [
        'l10n_ar_chart_generic',
        'account_voucher_withholding',
    ],
    'data': [
        'data/account_chart_respinsc.xml',
    ],
    'demo': [
        'demo/ri_withholding_demo.xml',
        'demo/ri_voucher_demo.xml',
    ],
    'test': [
    ],
    'installable': False,
    'auto_install': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
