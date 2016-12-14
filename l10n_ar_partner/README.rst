.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License

=====================================================
Títulos de Personería y Tipos de documentos Arentinos
=====================================================

Descripción funcional:
#. Agregado de tipos de documentos argentinos para identificar partners
#. Agregado de Títulos de personería comunmente utilizados en argentina (SA, SRL, Doctor, etc)
#. Por defecto se puede utilizar un solo documento por partner pero si quiere utilizar más puede activar esta opción en "Ventas / Configuración / Configuración / Partners / Permitir Múltiples Números de Identificación en partners"

Descripción técnica:
#. Hacemos algunas mejoras al módulo de partner identifications:
    * Agregamos secuencia a las categorías de ID
    * Agregamos secuencia a los id de un partner
    * Agregamos en partner un campo Main Id Category y un computado con inverso Main Id Number
    * Hacemos que los id categories puedan buscar por codigo y por nombre
#. Agregamos a partner el campo calculado "cuit" que devuelve un cuit o nada si no existe y además un método que puede ser llamado con .cuit_required() que devuelve el cuit o un error si no se encuentra ninguno.


Credits
=======

Contributors
------------

* Juan José Scarafía <jjs@adhoc.com.ar>

Maintainer
----------

.. image:: http://odoo-argentina.org/logo.png
   :alt: Odoo Argentina
   :target: http://odoo-argentina.org

This module is maintained by the Odoo Argentina.

Odoo Argentina, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-argentina.org
