.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===========================================
Argentinean Withholding Minimum for Neuquén
===========================================

Este módulo implementa:

* Para las retenciones de Ingresos Brutos cuya jurisdicción (``Jurisdiction`` /
  ``l10n_ar_state_id``) es **Neuquén**, el mínimo sujeto a retención (campo
  **Minimum Base** / ``l10n_ar_base_minimum_threshold``) se evalúa **por comprobante**:
  se compara contra la base imponible de **cada factura**, no contra la suma de las
  bases de todas las facturas del pago.

* Cuando un pago cancela **2 o más facturas**, el cálculo nativo suma todas las bases
  en una sola y compara ese total contra el mínimo. Este módulo, solo para Neuquén,
  retiene únicamente sobre las facturas cuya base imponible individual supera el
  mínimo, y deja fuera las que no lo alcanzan.

* En un **pago parcial** de una factura que supera el mínimo, se retiene sobre la base
  proporcional al importe pagado (prorrateo). El gate de base nativo anularía esa
  retención cuando el proporcional queda por debajo del mínimo; para Neuquén no se
  anula, porque la factura sí supera el mínimo (misma lógica que aplica ganancias).

* Refleja lo dispuesto por la Res. Gral. 276/DPR/17 (art. 10): el importe mínimo
  sujeto a retención debe analizarse sobre la base imponible correspondiente a cada
  comprobante. La base comparada es el neto para impuestos *IIBB Untaxed* (IVA
  discriminado) y el total para *IIBB Total Amount* (IVA no discriminado).

* Aplica **solo** cuando la jurisdicción del impuesto es Neuquén. Para el resto de las
  jurisdicciones el comportamiento no cambia.

* En las retenciones de Neuquén se completa el campo *Ref* con el detalle del cálculo
  del importe retenido (base * alícuota = importe), tal como lo hace ganancias. Para
  IIBB el estándar deja ese campo vacío.

* Aplica a facturas. Los adelantos puros (pagos sin comprobante asociado) mantienen el
  comportamiento nativo.


Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Definir en el impuesto de retención de IIBB la jurisdicción **Neuquén**
   (campo *Jurisdiction*).
#. Cargar el mínimo en el campo *Minimum Base* (``l10n_ar_base_minimum_threshold``).

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

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
