.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License

Módulo base de Contabilidad Argentina
=====================================

#. Create a purchases journals for "Liquidación de Impuestos", "Asientos de Apertura / Cierre" and "Sueldos y Jornales" on chart account installation

Sobre padron afip:
------------------

#. If you want to disable Title Case for afip retrived data, you can change or create a paremeter "use_title_case_on_padron_afip" with value False (by default title case is used)
#. para actualizar tenemos básicamente dos opciones:

    * Desde un partner cualquiera, si el mismo tiene configurado CUIT, entonces puede hacer click en el botón "Actualizar desde AFIP"
    * Hacerlo masivamente desde ""

Configuration
=============

TODO

Usage
=====

TODO

Know issues / Roadmap
=====================

Hay algunos problemas de redondeo según la configuración de precisión que se haga en el tipo "Precio de productos" y tip ode redondeo de la cia. Dejamos el análisis hasta ahora. (estos errores aparecen cuando se intenta validar contra afip)
ERROR 1: Los importes informados en AlicIVA no se corresponden con los porcentajes. es porque el importe de iva se calcula por línea y luego se suma. Este error se replica usando precisón de 2 para todo, round por linea y 4 lineas a 1.12

Amounts: Per line / globally. Donde el globally seria el mas real.

amount_untaxed 4.48 / 4.48
imp_total 5.44 / 5.42
imp_neto 4.48 / 4.48
imp_iva 0.96 / 0.94

Conclusión: se resuelve usando metodo "round globally" de la compañía, de esta manera el iva no se redondea en cada línea y se reporta correctamente

ERROR 2: AFIP Validation Error. 10048: El campo 'Importe Total' ImpTotal, debe ser igual a la suma de ImpTotConc + ImpNeto + ImpOpEx + ImpTrib + ImpIVA

AMOUNTS: Per line (funca) / globally prod en 4 decimales (funca) / globally prod en 2 decimales (funca). Donde 2 decimales es real pero queremos 4. 4 decimales tambien es real, calculos teoricos darían "36.6748, 7.7017 y 44.3765"
imp_total 44.40 / 44.39 / 44.39
imp_neto 36.69 / 36.670 (o 36.69 si usamos amount untaxed) / 36.69
imp_iva 7.71 / 7.700 / 7.70

Conclusión: este error solo se da si la precisión decimal de los precios de los productos es mayor a la precisión de la moneda. Esto se da porque el subtotal y el total de la factura se calculan usando los subtotales de las líneas que se redondean a la precisión de la moneda. Entonces el total no va a ser el total teorico de si se usarían mas decimales. Las alternativas son: a) usar precisión decimal para precio producto más baja. b) subir la precisión decimal de la moneda en cuestión (si es la moneda de la cia se exige tmb subir la precisión de "account")

ERROR 3: AFIP Validation Error. 10018: Si ImpIva es igual a 0 el objeto Iva y AlicIva son obligatorios. Id iva = 3 (iva 0)
Se dio en el caso de una factura que daba cero pero que se solucionaba también disminuyendo precisión decimal de 4 a 2 (y volviendo a calcula la línea de adelanto)

Credits
=======

Contributors
------------

* TODO

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
