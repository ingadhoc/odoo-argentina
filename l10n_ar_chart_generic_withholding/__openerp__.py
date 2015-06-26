# -*- coding: utf-8 -*-
{
    'name': 'Retenciones para Plan Contable General Argentino',
    'version': '2.7.155',
    'author':   'ADHOC SA',
    'category': 'Localization/Account Charts',
    'website':  'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'description': """
Retenciones para Plan Contable General Argentino
================================================
""",
    'depends': [
        'l10n_ar_chart_generic',
        'account_voucher_withholding',
    ],
    'demo': [
    ],
    'test': [
    ],
    'data': [
        'data/account_chart_respinsc.xml',
    ],
    'installable': True,
    'auto_install': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
