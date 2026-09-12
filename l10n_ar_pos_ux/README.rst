.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============================
Argentinian Point of Sale UX
==============================

Este módulo extiende el Point of Sale (POS) de Odoo para aplicar automáticamente percepciones y retenciones según la configuración de posiciones fiscales argentinas.

Características
===============

* **Percepciones automáticas en POS**: Cuando se crea una orden de venta desde el POS y el cliente tiene una posición fiscal configurada con percepciones (l10n_ar_tax), estas se agregan automáticamente a las líneas de la orden.

* **Integración con l10n_ar_tax**: Utiliza el mismo mecanismo de ``_l10n_ar_add_taxes()`` que se usa en facturas y órdenes de venta, garantizando consistencia en todo el sistema.

* **Cálculo por fecha**: Las percepciones se calculan correctamente según la fecha de la orden de POS y las alícuotas vigentes para el cliente.

Funcionamiento
==============

El módulo sobrescribe el método ``_get_tax_ids_after_fiscal_position`` de ``pos.order.line`` para:

1. Verificar si la orden tiene una posición fiscal con percepciones configuradas (``l10n_ar_tax_ids``)
2. Obtener la fecha de la orden
3. Llamar al método ``_l10n_ar_add_taxes()`` de la posición fiscal para obtener las percepciones aplicables
4. Agregar estas percepciones a los impuestos que ya fueron mapeados por la posición fiscal

Esto asegura que las percepciones se apliquen de la misma manera que en:

* Facturas (``account.move.line._get_computed_taxes``)
* Órdenes de venta (``sale.order.line._compute_tax_id``)

Instalación
===========

El módulo se instala de manera estándar como cualquier módulo de Odoo. Una vez instalado, las percepciones se aplicarán automáticamente en las ventas de POS según la configuración de las posiciones fiscales.

Uso
===

No requiere configuración adicional. El módulo funciona automáticamente una vez instalado, siempre que:

1. El cliente tenga una posición fiscal asignada
2. La posición fiscal tenga percepciones configuradas en el campo ``l10n_ar_tax_ids``
3. Las percepciones estén correctamente configuradas con sus alícuotas por cliente

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
