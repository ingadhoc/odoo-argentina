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
    # TODO lo ideal seria que el plan de cuentas se cargue en el modulo
    # pero luego no tenemos una manera facil de agregar estas retenciones,
    # habria que hacer alguna funcion que las sugiera y las haga. De paso dicha
    # funcion se utilizaria en casos donde se agrega a posteriori este modulo
        'demo/chart_demo.xml',
        'demo/ri_sale_invoice_demo.xml',
        'demo/ri_purchase_invoice_demo.xml',
        'demo/ri_voucher_demo.xml',
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
