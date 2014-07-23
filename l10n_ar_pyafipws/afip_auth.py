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
# Copyright 2013 by
# Based on code "factura_electronica" by Luis Falcon (GPLv3)
# Based on code by "openerp-iva-argentina" by Gerardo Allende / Daniel Blanco

"Authentication functions for Argentina's Federal Tax Agency (AFIP) webservices"

__author__ = "Mariano Reingart (reingart@gmail.com)"
__copyright__ = "Copyright (C) 2013 Mariano Reingart and others"
__license__ = "AGPL 3.0"

# Están muchos valores de importe con valor absoluto, puesto que el CAE
# en AFIP no acepta valores negativos.

import hashlib
import time
import os
import sys
import traceback


DEFAULT_TTL = 60*60*5       # five hours
WSAA_URL = ""               # change to production server (testing default)
PROXY = ""                  # proxy credentials and host
CACHE = ""                  # cache folder path, use default
DEBUG = False


def authenticate(service, certificate, private_key, force=False,
                 cache=CACHE, wsdl=WSAA_URL, proxy=PROXY, ):
    "Call AFIP Authentication webservice to get token & sign or error message"
    
    # import AFIP webservice authentication helper:
    from pyafipws.wsaa import WSAA
    
    # create AFIP webservice authentication helper instance:
    wsaa = WSAA()
    wsaa.LanzarExcepciones = True       # raise python exceptions on any failure
    
    # make md5 hash of the parameter for caching... 
    fn = "%s.xml" % hashlib.md5(service + certificate + private_key).hexdigest()
    if cache:
        fn = os.path.join(cache, fn)
    else:
        fn = os.path.join(wsaa.InstallDir, "cache", fn)

    try:
        # read the access ticket (if already authenticated)
        if not os.path.exists(fn) or \
           os.path.getmtime(fn)+(DEFAULT_TTL) < time.time():    
            # access ticket (TA) outdated, create new access request ticket (TRA) 
            tra = wsaa.CreateTRA(service=service, ttl=DEFAULT_TTL)
            # cryptographically sing the access ticket
            cms = wsaa.SignTRA(tra, certificate, private_key)
            # connect to the webservice:
            wsaa.Conectar(cache, wsdl, proxy)
            # call the remote method 
            ta = wsaa.LoginCMS(cms)
            if not ta:
                raise RuntimeError()
            # write the access ticket for further consumption
            open(fn, "w").write(ta)
        else:
            # get the access ticket from the previously written file
            ta = open(fn, "r").read()
        # analyze the access ticket xml and extract the relevant fields 
        wsaa.AnalizarXml(xml=ta)
        token = wsaa.ObtenerTagXml("token")
        sign = wsaa.ObtenerTagXml("sign")
        err_msg = None
    except:
        token = sign = None
        if wsaa.Excepcion:
            # get the exception already parsed by the helper
            err_msg = wsaa.Excepcion
        else:
            # avoid encoding problem when reporting exceptions to the user:
            err_msg = traceback.format_exception_only(sys.exc_type, 
                                                      sys.exc_value)[0]
        if DEBUG:
            raise
    return {'token': token, 'sign': sign, 'err_msg': err_msg}


if __name__ == '__main__':
    # basic tests:
    reingart_crt = open("./pyafipws/reingart.crt").read()
    reingart_key = open("./pyafipws/reingart.key").read()
    auth_data = authenticate("wsfe", reingart_crt, reingart_key, force=True)
    print auth_data
    assert auth_data['token']
    assert auth_data['sign']
    old_token = auth_data['token']
    auth_data = authenticate("wsfe", reingart_crt, reingart_key, force=True)
    assert auth_data['token'] == old_token
    import base64
    print base64.b64decode(auth_data['token'])
    print "ok."

