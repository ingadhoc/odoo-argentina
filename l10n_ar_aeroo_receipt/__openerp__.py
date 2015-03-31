# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Like Receipt Aeroo Report',
    'version': '1.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'summary': '',
    'description': """
Argentinian Like Receipt Aeroo Report
=====================================
Por defecto se utiliza el reporte "l10n_ar_aeroo_receipt/receipt.odt" que detalla los pagos en
* Cheques
* Banco
* Efectivo
Si se quiere detallar en función a los diarios se puede cambiar en configuracion/tecnico/aeroo reports/reports, ubicando el reporte "Argentinian Aeroo Receipt" en valor de template path por "l10n_ar_aeroo_receipt/receipt_journal_detail.odt"
    """,
    'author':  'Ingenieria ADHOC',
    'website': 'www.ingadhoc.com',
    'images': [
    ],
    'depends': [
        'report_extended_voucher_receipt',
        'account_check',
        'l10n_ar_aeroo_base',
        'l10n_ar_invoice',
    ],
    'data': [
        'receipt_report.xml',
        'voucher_receipt_template.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: