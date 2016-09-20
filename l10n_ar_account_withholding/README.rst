TODO
A script de instalación sumarle algo tipo esto, por ahora se puede correr manual. En realidad solo es necesario si estamos en localización o algo que requiera doble validation

UPDATE account_voucher SET retencion_ganancias='no_aplica' WHERE retencion_ganancias is null;


Tablas modificadas según: http://www.afip.gob.ar/noticias/20160526GananciasRegRetencionModificacion.asp

TODO
A impuestos de percepción de arba configurar Código Python:
result = price_unit * partner.get_arba_alicuota_percepcion()