.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==========================================
Argentinean Withholding Base for Santa Fe
==========================================

Este módulo implementa:

* En las retenciones de Ingresos Brutos de **Santa Fe**, la base imponible se toma del
  **tipo de contribuyente que informa el padrón PARP**: al contribuyente de **Convenio
  Multilateral** se le retiene sobre el **total** del comprobante y al **Local** sobre el
  **importe sin IVA**.

* El padrón informa ese dato en la posición 40 del diseño de registro (Anexo I de la
  RG 37/2025 de API Santa Fe): ``'C'`` = Convenio Multilateral, ``'D'`` = Local. El
  importador de alícuotas descarta esa columna, con lo cual sin este módulo se retiene a
  todos sobre el importe sin IVA y al de Convenio Multilateral se le retiene menos de lo
  debido.

* Refleja lo dispuesto por el art. 380 de la RG 36/2026 (Normativa Unificada de API Santa
  Fe): la regla general retiene «previa deducción de los conceptos que no integran la base
  imponible del gravamen» (base neta) y el apartado 1, para contribuyentes de Convenio
  Multilateral, «sobre el monto de cada pago sin deducción alguna» (base total).

* La base es una dimensión más en la búsqueda del impuesto: una retención del 0,6% sobre
  base neta y una del 0,6% sobre el total son impuestos distintos. Cuando en la base sólo
  existe el impuesto sobre base neta, la variante de Convenio Multilateral se crea
  copiándolo, con el sufijo **CM** en el nombre para poder distinguirlas en la interfaz.
  Esa variante no se puede elegir a mano como impuesto por defecto de la posición fiscal:
  la crea el padrón, y elegirla daría la base total también al contribuyente local. Se la
  reconoce por ese sufijo, así que un impuesto sobre el total configurado a propósito
  sigue siendo elegible.

* Una base total configurada a propósito en el impuesto de la posición fiscal (proveedor
  que no discrimina IVA) **no se pisa**: el contribuyente local no pide base, y se resuelve
  la del impuesto configurado.

* El CUIT que **no figura en el padrón** mantiene el comportamiento actual: alícuota de
  castigo con el impuesto por defecto de la línea, porque no se conoce su régimen.

* Aplica **sólo** a **retenciones** de la jurisdicción **Santa Fe**. En percepciones la base
  no cambia por el régimen de convenio (lo que define si se detrae el IVA es la condición del
  adquirente frente al IVA, art. 385 inc. j) pto. 2), y el 50% del art. 387 es otro
  mecanismo. En el resto de las jurisdicciones el comportamiento no cambia: ahí *IIBB Total
  Amount* es una base que se configura como cualquier otra (por ejemplo Neuquén, para
  comprobantes sin IVA discriminado).

Este módulo existe para 18.0 porque en 19.0 la funcionalidad está incorporada al módulo
``l10n_ar_tax``.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Definir en el impuesto de retención de IIBB la jurisdicción **Santa Fe**
   (campo *Jurisdiction*) y la base **IIBB Untaxed** (campo *WTH Tax*).
#. En la posición fiscal, dejar la línea de retención de Santa Fe con el tipo de consulta
   **Archivo de padrón**.
#. Cargar el padrón del período en *Contabilidad / Configuración / AFIP / Padrón de
   Alícuotas por compañía* (Santa Fe acepta solamente el archivo ZIP).

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
