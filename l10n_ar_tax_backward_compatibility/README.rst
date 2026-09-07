.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===============================================
Argentinian Withholdings backward compatibility
===============================================
How Odoo calculates income withholdings has varied substantially between versions 16, 17, and 18. This module is a technical module. Its objective is to allow continued calculation of accumulated withholdings in installations that migrate mid-period, or to perform the calculation of accumulated amounts in the months prior to migration when a payment is added in that period.

In addition to installing the module, it is necessary to migrate certain data available in previous versions.

If coming from an Odoo 16 installation:

* You must move the regime code from the ``payment.group`` model to the ``account.payment`` model, mark those payments as ``is_backward_withholding_payment``
* You must also move all withholding data from the payment model (``account.payment``) to the ``l10n_ar.payment.withholding`` model  and recalculate the ``regime_tax_id`` field..

    The fields are:

    ``automatic``,
    ``withholdable_invoiced_amount``,
    ``withholdable_advanced_amount``,
    ``accumulated_amount``,
    ``total_amount``,
    ``withholding_non_taxable_minimum``,
    ``withholding_non_taxable_amount``,
    ``withholdable_base_amount``,
    ``period_withholding_amount``,
    ``previous_withholding_amount``,
    ``computed_withholding_amount``.

If the source installation is Odoo 17:

* You only need to update the ``account.payment`` data by mapping the ``codigo_regimen`` to the new ``regime_code`` field, mark those payments as ``is_backward_withholding_payment``, and recalculate the ``regime_tax_id`` field.

Additionally, on databases with branches the migration unified the taxes of the child companies into the parent one: for each regime one ``account.tax`` stays active and its duplicate ends up archived. The journal items of the withholdings point to the surviving tax, while the payment withholding lines (``l10n_ar_withholding_line_ids``) may still point to the archived duplicate, so the strict match of ``account.move.line.withholding_id`` (from ``l10n_ar_tax``) finds nothing and every report reading that field breaks (SIFERE, SICORE, SIRCAR, Misiones, Santa Fe and PBA TXT files). This module adds a fallback: when the strict match fails, the withholding line is looked up by the identity of the regime (withholding payment type, tax type, jurisdiction and code, within the same company tree). It only applies to migrated data -one of the two taxes archived- and when there is a single candidate, so that a wrongly built new payment keeps failing visibly instead of being silently guessed.

-------------------------------------

La manera en que Odoo calcula las retenciones de ganancias ha variado sustancialmente entre las versiones 16, 17 y 18. Este módulo es un módulo técnico. Su objetivo es permitir seguir calculando retenciones acumuladas en instalaciones que migran en medio de un período, o realizar el cálculo de acumulados en los meses anteriores a la migración cuando se agrega un pago en ese período.

Además de instalar el módulo, es necesario migrar ciertos datos disponibles en versiones anteriores.

Si viene de una instalación de Odoo 16:

*   Debe mover el código de régimen desde el modelo ``payment.group`` al modelo ``account.payment``, marcar esos pagos como ``is_backward_withholding_payment`` .
*   También debe mover todos los datos sobre retención del modelo de pago (``account.payment``) al modelo ``l10n_ar.payment.withholding`` y recalcular el campo ``regime_tax_id``.

    Los campos son:

    ``automatic``,
    ``withholdable_invoiced_amount``,
    ``withholdable_advanced_amount``,
    ``accumulated_amount``,
    ``total_amount``,
    ``withholding_non_taxable_minimum``,
    ``withholding_non_taxable_amount``,
    ``withholdable_base_amount``,
    ``period_withholding_amount``,
    ``previous_withholding_amount``,
    ``computed_withholding_amount``.

Si la instalación de origen es de Odoo 17:

*   Solo debe actualizar los datos de ``account.payment`` mapeando el ``codigo_regimen`` al nuevo campo ``regime_code``, marcar esos pagos como ``is_backward_withholding_payment`` y recalcular el campo ``regime_tax_id``.

Adicionalmente, en bases con sucursales la migración unificó los impuestos de las compañías hijas en la compañía padre: de cada régimen queda un ``account.tax`` activo y su duplicado archivado. Los apuntes contables de las retenciones quedan apuntando al impuesto superviviente, mientras que las líneas de retención del pago (``l10n_ar_withholding_line_ids``) pueden seguir apuntando al duplicado archivado, con lo cual el match estricto de ``account.move.line.withholding_id`` (de ``l10n_ar_tax``) no encuentra nada y se rompen todos los reportes que leen ese campo (los TXT de SIFERE, SICORE, SIRCAR, Misiones, Santa Fe y PBA). Este módulo agrega un fallback: cuando el match estricto falla, la línea de retención se busca por la identidad del régimen (tipo de pago de la retención, tipo de impuesto, jurisdicción y código, dentro del mismo árbol de compañías). Solo aplica a data migrada -alguno de los dos impuestos archivado- y si hay una única candidata, para que un pago nuevo mal armado siga fallando de forma visible en vez de resolverse por adivinanza.

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
