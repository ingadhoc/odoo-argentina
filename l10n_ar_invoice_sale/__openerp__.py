# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Sale Total Fields',
    'version': '8.0.1.0.1',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author':  'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Argentinian Sale Total Fields
=============================
Add fields in sale orders so that you can print sale orders with vay included or not depending on VAT responsabilities
NOTAS PARA MEJORAR Y TRADUCIR:
* Para usar esta funcionalidad tnees que ir a la compania, pestañá config, grupo "sale" y setear si querés y el valor por defecto que querés que tome si no hay match (para el caso de facu sería "no_discriminated_default" de (manera predeterminada no se discrimnan los impuestos, es decir que si n tiene seteado nada el partner entonces no se discrimina)
* En los presupuestos, igualmente, si lo quiere cambiar ,en la segunda pestaña hay un campo "vat discriminated", abajo de posición fiscal, donde se 
    """,
    'depends': [
        'sale',
        'l10n_ar_invoice',
    ],
    'external_dependencies': {
    },
    'data': [
        'security/invoice_sale_security.xml',
        'sale_view.xml',
        'report/invoice_report_view.xml',
        'res_company_view.xml',
        # 'res_config_view.xml',
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
