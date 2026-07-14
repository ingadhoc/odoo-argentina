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
  ``l10n_ar_state_id``) es **Neuquén**, el mínimo sujeto a retención cargado en el
  campo **Minimum Base** (``l10n_ar_base_minimum_threshold``) se evalúa sobre el
  **neto total de la factura** (base imponible sin impuestos): si no supera ese
  mínimo, no se practica la retención.

* El gate estándar de ese campo compara contra la base retenida (``base_amount``),
  que para impuestos de tipo *IIBB Total Amount* es el total con impuestos y en pagos
  parciales es el neto proporcional al residual pagado. Este módulo, solo para
  Neuquén, lo compara contra el neto total de la/s factura/s — ni el total con
  impuestos ni el monto del pago.

* Refleja lo dispuesto por la Res. Gral. 276/DPR/17 (art. 10): el importe mínimo
  sujeto a retención debe analizarse siempre sobre la base imponible; cuando la
  factura discrimina IVA, dicho importe se deduce para la comparación contra el mínimo.

* Aplica **solo** cuando la jurisdicción del impuesto es Neuquén. Para el resto de las
  jurisdicciones el comportamiento no cambia.


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
