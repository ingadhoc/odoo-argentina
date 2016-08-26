Modulo Base para los Web Services de AFIP
=========================================

Homologation / production:
--------------------------

First it search for a paramter "afip.ws.env.type" if exists and:

* is production --> production
* is homologation --> homologation

Else

Search for 'server_mode' parameter on conf file. If that parameter:

* has a value then we use "homologation",
* if no parameter, then "production"

Incluye:
--------

* Wizard para instalar los claves para acceder a las Web Services.
* API para realizar consultas en la Web Services desde OpenERP.

El módulo l10n_ar_afipws permite a OpenERP acceder a los servicios del AFIP a
travésde Web Services. Este módulo es un servicio para administradores y
programadores, donde podrían configurar el servidor, la autentificación
y además tendrán acceso a una API genérica en Python para utilizar los
servicios AFIP.

Para poder ejecutar los tests es necesario cargar la clave privada y el
certificado al archivo test_key.yml.

Tenga en cuenta que estas claves son personales y pueden traer conflicto
publicarlas en los repositorios públicos.