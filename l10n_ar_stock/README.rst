.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===========================================================
Integración del módulo de stock a requerimientos argentinos
===========================================================

#. Remito electrónico Argentino
#. Número de despacho en lotes

Sobre remito electrónico
------------------------

PENDIENTE:

* validaciones formato patentes (3 letras y 3 números ó 2 letras, 3 números y 2 letras)
* parsear datetime_out y validar fecha >= hoy-1 y menor= a hoy mas 30 (no tan necesario, ya lo valida la respuesta, por ahora en el help)
* Implementar, si es necesario, nro_planta y nro_puerta
* Si es necesario o mejor imprimir el número obtenido en el remito, entonces tenemos que ver que las dos cosas se hagan en el mismo momento (reporte de remito y solicitud de cot)


IMPORTANTE: por ahora está implementado para stock.picking pero no seria muy dificil implementarlo también para facturas ya que la factura puede ser el comprobante de entrega (ver documentos de más abajo)

Por ahora implementados ARBA y Santa Fe.

* Tabla de códigos (Según arba): http://www.arba.gov.ar/bajadas/Fiscalizacion/Operativos/TransporteBienes/Documentacion/20080701-TB-TablasDeValidacion.pdf
* Tablas de códigos (Según santa fe): https://www.santafe.gov.ar/index.php/content/download/72020/349107/file/Descargar (igual a la de arba)
* Tabla en sistemas ágiles: http://www.sistemasagiles.com.ar/trac/wiki/RemitoElectronicoCotArba?format=pdf
* Especificación archivo txt: http://www.arba.gov.ar/Transporte_Bienes/VerPDF.asp?param=DA
* Nomenclador productos: https://www.arba.gov.ar/Aplicaciones/NomencladorTB/NomencladorTB.asp

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Nothing to configure

Usage
=====

To use this module, you need to:


.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/argentina-sale/issues>`_. In case of trouble, please
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
