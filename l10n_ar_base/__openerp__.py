# -*- coding: utf-8 -*-


{
    'name': 'Argentinian Localization',
    'version': '1.0',
    'category': 'Argentinian Localization',
    'sequence': 14,
    'summary': 'localization, argentina, configuration',
    'description': """
Provides the configuration for whole business suite according to Argentinian Localization.
==========================================================================================
Algunas ideas en torno a esta localización:
    Se usan los reportes de Aeroo porque son facilmente customizables para cada Cliente
    El módulo l10n_ar_invoice tiene toda la lógica de impuestos y tipos de documentos de la afip, probablemente sea mejor renombrarloa l10n_ar_afip o l10n_ar_documents o l10n_ar_account
    Respecto a los impuestos y como identificamos si son IVA, iibb, drei, retencion, percepcion, etc. Si bien todavía no lo usamos, la idea es hacerlo por un ilike al nombre donde
        Si el nombre del padre tiene "IVA" es IVA
        Si el nombre del padre tiene "IIBB" es IIBB
        Si el nombre del padre tiene "DREI" es DREI
        Si el nombre del padre tiene "Ganancias" es Ganancias
        Si el nombre del padre tiene "RETENCION" es RETENCION
        Si el nombre del padre tiene "PERCEPCION" es PERCEPCION
    Todo el analisis de impuestos se debería hacer so bre account move lines consultando el tax.code (los tax no interesan)
    Si una retención o impuesto ya fue conciliado o no, lo vamos a saber agregando un m2o en account.move.line apuntando a nuestro "vat.ledger" o como se llame esa clase
    Por ahora, que no hay impuestos y percepeciones automáticas.
        Si yo tengo que cargar percepciones en una compra:
            Alternativa 1 (sin desarrollo)
                Creamos productos tipo "servicio" para cada percepción dentro de una categoría "Impuestos", asociadas a un impuesto de esa percepción, con código python "result = price_unit" e "impuestos incluidos en el precio". Son productos que solo se pueden comprar.
                Luego se agregan dichos productos en la factura de compras, completando el importe correspondiente.
            Atlernativa 2 (con modulo "account_invoice_manual_tax")
                Modificamos la vista de impuestos en facturas para que permita elegir código de impuestos. 
                La ventaja de esto es que ya nos permite utilizar esto en percepciones de venta sin que hayamos que se carguen manualmente.
        Si yo tengo que cargar retenciones en un cobro:
            TODO
        Si yo tengo que aplicar percepciones en una venta
            TODO pero la idea sería usar algo de posiciones fiscales o similar y terminar 
        Si yo tengo que aplicar retenciones en un pago:
            TODO


Features
+++++++++++++++
Product Features
--------------------
TODO


Warehouse Features
------------------------
TODO

Sales Features
--------------------
TODO

* TODO1
* TODO2
* TODO3

Purchase Features
-------------------------
TODO

* TODO1
* TODO2

Finance Features
------------------
TODO

Extra Tools
-------------
TODO

* TODO1
* TODO2
    """,
    'author':  'Ingenieria ADHOC',
    'website': 'www.ingadhoc.com',
    'images': [
    ],
    'depends': [
        'base_setup'
    ],
    'data': [
        'l10n_ar_base_groups.xml',
        'res_config_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': True,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: