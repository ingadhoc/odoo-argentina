.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============================================
Automatic Argentinian Withholdings on Payments
==============================================

Tablas modificadas según: http://www.afip.gob.ar/noticias/20160526GananciasRegRetencionModificacion.asp

TODO:
    -A script de instalación sumarle algo tipo esto, por ahora se puede correr manual. En realidad solo es necesario si estamos en localización o algo que requiera doble validation
    -UPDATE account_payment_group SET retencion_ganancias='no_aplica' WHERE retencion_ganancias is null;
    - el ajuste de calculo de impuestos en pedidos de venta (por compatibilidad con arba) lo hicimos en sale_usability, habria que hacerlo en un modulo de la localización

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
