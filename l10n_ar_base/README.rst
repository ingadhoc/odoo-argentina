.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

========================================
Base Module for Argentinian Localization
========================================

Este modulo basicamente hace:
1. Poner como dato demo a la companía como pais "Argentina" para que todos los tests y planes de cuenta que se instalan sean de argentina
2. Sobreescribir para que cuando se instale un plan de cuentas automáticamente para el país argentina, se instale "l10n_ar_chart" en vez de "l10n_ar"

Algunas ideas en torno a esta localización:
===========================================

* Se usan los reportes de Aeroo porque son facilmente customizables para cada Cliente
* El módulo l10n_ar_account tiene toda la lógica de impuestos y tipos de documentos de la afip, probablemente sea mejor renombrarloa l10n_ar_afip o l10n_ar_documents o l10n_ar_account
* Respecto a los impuestos y como identificamos si son IVA, iibb, drei, retencion, percepcion, etc. Si bien todavía no lo usamos, la idea es hacerlo por un ilike al nombre donde:
    * Si el nombre del padre tiene "IVA" es IVA
    * Si el nombre del padre tiene "IIBB" es IIBB
    * Si el nombre del padre tiene "DREI" es DREI
    * Si el nombre del padre tiene "Ganancias" es Ganancias
    * Si el nombre del padre tiene "RETENCION" es RETENCION
    * Si el nombre del padre tiene "PERCEPCION" es PERCEPCION
* Todo el analisis de impuestos se debería hacer so bre account move lines consultando el tax.code (los tax no interesan)
* Si una retención o impuesto ya fue conciliado o no, lo vamos a saber agregando un m2o en account.move.line apuntando a nuestro "vat.ledger" o como se llame esa clase
* Por ahora, que no hay impuestos y percepeciones automáticas.
    * Si yo tengo que cargar percepciones en una compra:
        * Alternativa 1 (sin desarrollo)
            * Creamos productos tipo "servicio" para cada percepción dentro de una categoría "Impuestos", asociadas a un impuesto de esa percepción, con código python "result = price_unit" e "impuestos incluidos en el precio". Son productos que solo se pueden comprar.
            * Luego se agregan dichos productos en la factura de compras, completando el importe correspondiente.
        * Atlernativa 2 (con modulo "account_invoice_manual_tax")
            * Modificamos la vista de impuestos en facturas para que permita elegir código de impuestos.
            * La ventaja de esto es que ya nos permite utilizar esto en percepciones de venta sin que hayamos que se carguen manualmente.
    * Si yo tengo que cargar retenciones en un cobro:
        * TODO
    * Si yo tengo que aplicar percepciones en una venta
        * TODO pero la idea sería usar algo de posiciones fiscales o similar y terminar
    * Si yo tengo que aplicar retenciones en un pago:
        * TODO

Installation
============

To install this module, you need to:

#. Do this ...

Configuration
=============

To configure this module, you need to:

#. Go to ...

Usage
=====

To use this module, you need to:

#. Go to ...

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/odoo-argentina/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
