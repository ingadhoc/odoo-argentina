# -*- coding: utf-8 -*-
#!/usr/bin/python

import sys, urllib, hashlib, os, os.path, pickle
from geopy import geocoders
from types import GeneratorType

gc = geocoders.Google('ABQIAAAAMWm7ddpoRV3HO0u7NtA_IhRTfPMBNX3pvExQyYBKj7aZZJK5lxQYw0LDgWXedvepzKpGxQKf-kmN3A')

def urlopen(url):
    print >> sys.stderr, "Urlopen reading:", url
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
    m = hashlib.new('ripemd160')
    m.update(input_string)
    m.update(pickle.dumps(args))
    tmpfilename = "cache/geocode_%s" % m.hexdigest()
    if not os.path.exists(tmpfilename):
        geocode_out = gc.geocode(input_string, **args)
        if isinstance(geocode_out, GeneratorType):
            geocode_out = list(geocode_out)
        pickle.dump(geocode_out, open(tmpfilename, 'w'))
    else:
        geocode_out = pickle.load(open(tmpfilename))

    return geocode_out

