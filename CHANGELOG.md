### Odoo-Argentina

#### CHANGELOG
##### 8.0.1 to 8.0.2
* Se depreciaron l10n_ar_wsafip y l10n_ar_wsafip_fe
* En su reemplazo se van a utilizar l10n_ar_afipws y l10n_ar_afipws_fe
* Estos nuevos modulos utilizan el proyecto pyafipws
* Se mejoraron los datos demo

###### UPGRADE 8.0 to 8.0.1
- pull odoo-support (solo interesante para ADHOC)
- cambiar docker a 8.0.3 - create update
- pull de odoo argentina en 8.0.2 (primero en test luego en prod)
- reiniciar instacia 
- actualizar listado de modulos 
- idealmente sacar a todas las cuentas contables que tengan "type check" (no hace falta en el plan de cuentas template)
- hacer backup de la pkey y cert
- desinstalar wsafip
- reiniciar instancia
- actualizar l10n_ar_invoice
- cargar pkey y cert nuevos (o utilizar los del server y asignar en afip)
- instalar afipws_fe
- instalar server_mode_fetchmail (solo interesante para ADHOC)
- ir a puntos de venta y setear electronica al que corresponda
- Si da un error probar borrar la afip session 

##### 8.0 to 8.0.1
* Las modificación más fuerte tiene que ver con algunos campos que se agregaron a códigos de impuestos (tipo de impuesto, donde aplica, etc). Si lago da error lo más probable es que tenga que ver con esto.
* Para poder apretar el boton de "Compute citi data" se requiere que el libro iva esté en borrador
* Estas modificaciones son principalmente utilizadas en tres cosas:
    * A la hora de validar una factura electronica, se debe indicar que impuestos son IVA, percepeciones, etc, etc
    * A la hora de generar los archivos del citi, se requiere informar tmb que es percepecion nacional, prov, municipal, que es percepeción de iva, etc..
    * Agregué una validación a la hora de validar facturas "argentinas" para que no deje hacerlo si los impuestos no tienen configurados códigos de impuestos o los códigos no tienen seteados estos atributos nuevos
* Errores en generación de archivo citi:
    * Los mensajes de errores deberían ayudar a identificar que error puede estar ocurriendo, lo más probable es que tenga que ver con que falta el cuit de un prov o algo por el estilo
* Errores en la importación de los archivos citi:
    * Cada uno de los errores indica en que línea está ocurriendo. Dicho numero de linea se corresponde con el orden de las facturas que se ven en el libro iva

###### UPGRADE 8.0 to 8.0.1
- Actualziar l10n_ar_invoice
- Configurar atributos de codigos de impuestos