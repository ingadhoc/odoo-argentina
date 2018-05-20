.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=====================================================
Títulos de Personería y Tipos de documentos Arentinos
=====================================================

Descripción funcional:
----------------------

#. Agregado de tipos de documentos argentinos para identificar partners
#. Agregado de Títulos de personería comunmente utilizados en argentina (SA, SRL, Doctor, etc)
#. Por defecto se puede utilizar un solo documento por partner pero si quiere utilizar más puede activar esta opción en "Ventas / Configuración / Configuración / Partners / Permitir Múltiples Números de Identificación en partners"

Descripción técnica:
--------------------

#. Hacemos algunas mejoras al módulo de partner identifications:

    * Agregamos secuencia a las categorías de ID
    * Agregamos secuencia a los id de un partner
    * Agregamos en partner un campo Main Id Category y un computado con inverso Main Id Number
    * Hacemos que los id categories puedan buscar por codigo y por nombre
#. Agregamos a partner el campo calculado "cuit" que devuelve un cuit o nada si no existe y además un método que puede ser llamado con .cuit_required() que devuelve el cuit o un error si no se encuentra ninguno.

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
