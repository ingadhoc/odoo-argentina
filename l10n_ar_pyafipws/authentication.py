#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the Affero GNU General Public License as published by
# the Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# Copyright 2013 by Mariano Reingart
# Based on code "factura_electronica" by Luis Falcon 
# Based on code "openerp-iva-argentina" by Gerardo Allende / Daniel Blanco
# Based on code "l10n_ar_wsafip" by OpenERP - Team de Localización Argentina

"Credentials for Argentina Federal Tax Administration (AFIP) webservices"

__author__ = "Mariano Reingart (reingart@gmail.com)"
__copyright__ = "Copyright (C) 2013 Mariano Reingart and others"
__license__ = "AGPL 3.0+"

from osv import fields, osv
try:
    from openerp.tools.translate import _
except:
    _ = str
    
DEBUG = True


class company_pyafipws_credentials(osv.osv):
    _name = "res.company"
    _inherit = "res.company"
    _columns = {
        'pyafipws_cuit': fields.char('CUIT AFIP WS', size=15, 
            help="CUIT de la empresa habilitado para operar webservices AFIP"),
        'pyafipws_certificate': fields.text('Certificado AFIP WS',
            help="Certificado (.crt) de la empresa para webservices AFIP"),
        'pyafipws_private_key': fields.text('Clave Privada AFIP WS',
            help="Clave Privada (.key) de la empresa para webservices AFIP"),
    }
    
    def pyafipws_authenticate(self, cr, uid, ids, context=None, service="wsfe"):
        "Authenticate against AFIP, returns token, sign, err_msg (dict)"
        import afip_auth
        auth_data = {}
        for company in self.browse(cr, uid, ids):
            # get the authentication credentials:
            certificate = str(company.pyafipws_certificate)
            private_key = str(company.pyafipws_private_key)
            # create the proxy and get the configuration system parameters:
            cfg = self.pool.get('ir.config_parameter')
            cache = cfg.get_param(cr, uid, 'pyafipws.cache', context=context)
            proxy = cfg.get_param(cr, uid, 'pyafipws.proxy', context=context)
            wsdl = cfg.get_param(cr, uid, 'pyafipws.wsaa.url', context=context)
            # call the helper function to obtain the access ticket:
            auth = afip_auth.authenticate(service, certificate, private_key,
                                          cache=cache or "", wsdl=wsdl or "", 
                                          proxy=proxy or "")
            auth_data.update(auth)
        return auth_data

    def test_pyafipws_authentication(self, cr, uid, ids, context=None):
        auth_data = self.pyafipws_authenticate(cr, uid, ids)
        #self.log(cr, uid, ids[0], "test_afip_auth: %s" % auth_data)        
        from base64 import b64decode
        if auth_data['token']:
            msg = b64decode(auth_data['token'])
            raise osv.except_osv(_("OK"), msg)
        else:
            msg = auth_data['err_msg']
            raise osv.except_osv(_("ERROR"), msg)
        return {}


company_pyafipws_credentials()


if __name__ == "__main__":
    # basic tests:
    from osv import cursor
    mycompany = company_pyafipws_credentials()
    auth_data = mycompany.pyafipws_authenticate(cursor(), None, [1], service="wsfe")
    print auth_data
    assert auth_data['token']
    assert auth_data['sign']
    old_token = auth_data['token']
    auth_data = mycompany.pyafipws_authenticate(cursor(), None, [1], service="wsfe")
    assert auth_data['token'] == old_token
    ta = mycompany.test_pyafipws_authentication(cursor(), None, [1])
    print ta
    print "ok."
    
