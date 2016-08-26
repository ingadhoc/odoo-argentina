# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut
    gc = Nominatim(timeout=3)
except ImportError:
    gc = None
    GeocoderTimedOut = None
    _logger.warning("Please, install geopy using 'pip install geopy'.")

import urllib
import hashlib
import os
import os.path
import pickle


def urlopen(url):
    basedir = os.path.join(os.getcwd(), 'cache')
    m = hashlib.new('ripemd160')
    m.update(url)
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    tmpfilename = os.path.join(basedir, "urlopen_%s" % m.hexdigest())
    if not os.path.exists(tmpfilename):
        filename, header = urllib.urlretrieve(url, tmpfilename)
    return open(tmpfilename)


def geocode(input_string, **args):
    if gc is None:
        return None
    m = hashlib.new('ripemd160')
    m.update(input_string)
    m.update(pickle.dumps(args))
    tmpfilename = "cache/geocode_%s" % m.hexdigest()
    if not os.path.exists(tmpfilename):
        geocode_out = gc.geocode(input_string, **args)
        if geocode_out is None:
            # Not found
            response = []
        elif isinstance(geocode_out, list):
            # Found more than one
            response = [_gc.raw for _gc in geocode_out]
        else:
            # Found one
            response = [geocode_out.raw]
        pickle.dump(response, open(tmpfilename, 'w'))
    else:
        response = pickle.load(open(tmpfilename))

    return response

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
