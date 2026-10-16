.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

======================================
Argentinian Withholdings + Perceptions
======================================

Este módulo imlementa:

* Add tags on ar taxes repartition lines.
* Add fiscal position demo records.
* Reglas de percepciones en notas de crédito por jurisdicción (AGIP y ARBA: solo en anulaciones totales; AGIP además hasta 2 períodos mensuales siguientes a la factura). En las anulaciones totales, la NC lleva las percepciones de AGIP y ARBA de la factura que anula; el resto de las jurisdicciones no cambia. Se activan con el parámetro de sistema ``l10n_ar_tax.credit_note_perception_rules`` en ``True``, que aplica a todas las compañías de la base.
* Importador de Padrón PARP ret y perc SF - Santa Fe y ARBA. Especificación: "Api - Rg 37 2025 Anexo I.pdf" y archivo de ejemplo de padrón "PARP_999999_ejemplo_padron_santa_fe.csv" para el mes de marzo 2026. Ambos archivos se encuentran en la carpeta "doc/padron_santa_fe" de este módulo. Configuraciones manuales: duplicar impuesto de retención y percepción aplicada de Santa Fe y colocarle alícuota 5% al de retención y 6% al de percepción; dichos impuestos tienen alícuota 'castigo', es decir, si el contribuyente no se encuentra en el padrón y no está exento entonces se le aplicará dicha alícuota. Dichos impuestos con alícuota castigo deben ser asignados como impuesto por defecto en la posición fiscal correspondiente y en dicha posición fiscal elegir webservice: padron.

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
