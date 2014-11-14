# -*- coding: utf-8 -*-
{
    "name": "Adjust Account Follow UP for Argentinian Localization",
    "version": "1.0",
    'author':  'Ingeniería ADHOC',
    'website': 'www.ingadhoc.com',
    "category": "Accounting",
    "description": """
Adjust Account Follow UP for Argentinian Localization
=====================================================
    """,
    'depends': [
        'account_followup',
        'l10n_ar_invoice',
    ],
    'data': [
        'account_move_line_view.xml',
        'partner_view.xml',
        'wizard/account_company_followup_wizard.xml',
        'views/report_followup.xml',
        'views/customer_followup__view.xml',
        'views/account_company_select.xml',

    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
