# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Currency Rate Update',
    'version': '1.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'summary': '',
    'description': """
Argentinian Currency Rate Update
================================
    """,
    'author':  'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'images': [
    ],
    'depends': [
        'currency_rate_update',
        'l10n_ar_afipws_fe',
    ],
    'data': [
        'views/currency_rate_update_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
