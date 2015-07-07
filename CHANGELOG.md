### Odoo-Argentina

#### WISHLIST
* Eliminar dependencias de odoo-argentina (pyopenssl, etc)
* Probar generar pkey, cert. request y demás usando pyafipws (limpiar modulos afipws y afipws_fe). Ejemplo en https://code.google.com/p/pyafipws/wiki/FacturaElectronicaPython
* separar partner en l10n_..invoice (mods en base vat o en otro lugar tipo l10n_ar_partner) para que si quiereo cuit y cosas asi no requiera instalar account
* Ver si simplificamos el manejo de documentos y el vat
* mejorar la parte de certificado, el campo state por ahí no neesario en el alias. A su vez tal ves el "outsorced" no es mas necesario, siempre se genera para la compania, tal vez no hacemos los dos m2o si no que agregamos todo a la clase res.company y listo

#### CHANGELOG
##### 8.0.1 to 8.0.2
* Se depreciaron l10n_ar_wsafip y l10n_ar_wsafip_fe
* En su reemplazo se van a utilizar l10n_ar_afipws y l10n_ar_afipws_fe
* Estos nuevos modulos utilizan el proyecto pyafipws
* Se mejoraron los datos demo

###### UPGRADE 8.0 to 8.0.2
Idem 8.0.1 + Configurar atributos de codigos de impuestos

###### UPGRADE 8.0.1 to 8.0.2
En intancia test (solo interesane para ADHOC):
- pull odoo-support
- pull de odoo argentina en 8.0.2
- cambiar docker a 8.0.3 - create update
- probar acceder

En instancia de produccion
- cambiar las cuentas contables que tengan "type check" por "Efectivo" (no hace falta en el plan de cuentas template)
- pull odoo-support (solo interesante para ADHOC)
- cambiar docker a 8.0.3
- pull de odoo argentina en 8.0.2
- create/update instancia
- update a l10n_ar_invoice (esto dispara update de l10n_ar_wsafip_fe tmb)
- hacer backup de la pkey y cert
- desinstalar l10n_ar_wsafip_fe
- reiniciar instacia 
- actualizar listado de modulos
- actualizar l10n_ar_invoice (para que ande bien export haría falta hacer un -i o hacer una cargamanual de los csv de uom, currency y countries)
- cargar pkey y cert nuevos (o utilizar los del server y asignar en afip)
- instalar afipws_fe
- instalar server_mode_fetchmail (solo interesante para ADHOC)
- ir a puntos de venta y setear electronica al que corresponda

###### NOTAS VARIAS
PARA PROBAR EN DOCKER
sudo docker run -ti -p 127.0.0.1:8069:8069 -u root --link db:db --name odoo-fe adhoc/odoo-adhoc:8.0.2 /bin/bash
runuser -u odoo openerp-server -- -c /etc/odoo/openerp-server.conf --logfile=False
git clone https://github.com/ingadhoc/odoo-argentina -b 8.0.2
git clone https://github.com/oca/web -b 8.0
runuser -u odoo openerp-server -- -c /etc/odoo/openerp-server.conf --logfile=False --addons-path=/usr/lib/python2.7/dist-packages/openerp/addons,/odoo-argentina,/web -s
runuser -u odoo openerp-server -- -c /etc/odoo/openerp-server.conf --logfile=False

PARA PROBAR EN VIRTUALENV
sudo apt-get install python-dev swig python-virtualenv mercurial python-pip libssl-dev
hg clone https://code.google.com/p/pyafipws
cd pyafipws
(con ambiente activado)
pip install -r requirements.txt
python setup.py install

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