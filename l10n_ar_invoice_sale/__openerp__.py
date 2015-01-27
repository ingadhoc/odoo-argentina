# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Sale Total Fields',
    'version': '1.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'summary': '',
    'description': """
Argentinian Sale Total Fields
=============================
Add fields in sale orders so that you can print sale orders with vay included or not depending on VAT responsabilities
NOTAS PARA MEJORAR Y TRADUCIR:
* Para usar esta funcionalidad tnees que ir a la compania, pestañá config, grupo "sale" y setear si querés y el valor por defecto que querés que tome si no hay match (para el caso de facu sería "no_discriminated_default" de (manera predeterminada no se discrimnan los impuestos, es decir que si n tiene seteado nada el partner entonces no se discrimina)
* En los presupuestos, igualmente, si lo quiere cambiar ,en la segunda pestaña hay un campo "vat discriminated", abajo de posición fiscal, donde se 
    """,
    'author':  'Ingenieria ADHOC',
    'website': 'www.ingadhoc.com',
    'images': [
    ],
    'depends': [
        'sale',
        'l10n_ar_invoice',
    ],
    'data': [
        'security/invoice_sale_security.xml',
        'sale_view.xml',
        'report/invoice_report_view.xml',
        'res_company_view.xml',
        'res_config_view.xml',
        'security/ir.model.access.csv',
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
