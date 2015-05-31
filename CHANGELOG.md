### Odoo-Argentina

#### CHANGELOG
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

#### UPGRADE 8.0 to 8.0.1
- Actualziar l10n_ar_invoice
- Configurar atributos de codigos de impuestos