# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    _logger.warning("Please, install BeautifulSoup using"
                    " 'pip install beautifulsoup'.")

import re
from strcmp import mostequivalent
from cache import urlopen, geocode, GeocoderTimedOut
import unicodedata

codprov_dict = {
    'argentina': {
        'buenos aires': 'B',
        'buenos aires province': 'B',
        'catamarca': 'K',
        'chaco': 'H',
        'chubut': 'U',
        'cordoba': 'X',
        'corrientes': 'W',
        'entre rios': 'E',
        'formosa': 'P',
        'jujuy': 'Y',
        'la pampa': 'L',
        'la rioja': 'F',
        'mendoza': 'M',
        'misiones': 'N',
        'neuquen': 'Q',
        'rio negro': 'R',
        'salta': 'A',
        'san juan': 'J',
        'san luis': 'D',
        'santa cruz': 'Z',
        'santa fe': 'S',
        'santiago del estero': 'G',
        'tierra del fuego': 'V',
        'tucuman': 'T',
    }
}

address_re = [
    re.compile(
        r"\s*((?P<building>[\w\s]+)\s*,)?"
        r"\s*((?P<number>[\d]+)\s*,)"
        r"\s*((?P<street>[\w\s]+)\s*,)"
        r"\s*(\s*((?P<subnbhd>[\w\s]+)\s*,)?(?P<nbhd>[\w\s]+)\s*,)?"
        r"\s*((?P<city>(?P<state>Ciudad Aut.*noma de Buenos Aires))\s*,)"
        r"\s*((?P<zip>(C)?\d\d\d\d(\w\w\w)?)\s*,)?"
        r"\s*(?P<country>[Aa]rgentina)", re.UNICODE),
    re.compile(
        r"\s*((?P<building>)\s*,)?"
        r"\s*((?P<number>[\d]+)\s*,)?"
        r"\s*((?P<street>[\w\s]+)\s*,)"
        r"\s*(\s*((?P<subnbhd>[\w\s]+)\s*,)?(?P<nbhd>[\w\s]+)\s*,)?"
        r"\s*((?P<city>(?P<state>Ciudad Aut.*noma de Buenos Aires))\s*,)"
        r"\s*((?P<zip>(C)?\d\d\d\d(\w\w\w)?)\s*,)?"
        r"\s*(?P<country>[Aa]rgentina)", re.UNICODE),
    re.compile(
        r"\s*((?P<building>[\w\s]+)\s*,)?"
        r"\s*((?P<number>[\d]+)\s*,)?"
        r"\s*((?P<street>[\w\s]+)\s*,)"
        r"\s*(\s*((?P<subnbhd>[\w\s]+)\s*,)?(?P<nbhd>[\w\s]+)\s*,)?"
        r"\s*((?P<city>[\w\s]+)\s*,)"
        r"\s*((?P<state>[\w\s]+)\s*,)"
        r"\s*((?P<zip>\w?\d\d\d\d(\w\w\w)?)\s*,)?"
        r"\s*(?P<country>[Aa]rgentina)", re.UNICODE),
    re.compile(
        r"\s*((?P<building>[\w\s]+)\s*,)?"
        r"\s*((?P<number>[\d]+)\s*,)"
        r"\s*((?P<street>[\w\s]+)\s*,)"
        r"\s*(\s*((?P<subnbhd>[\w\s]+)\s*,)?(?P<nbhd>[\w\s]+)\s*,)?"
        r"\s*((?P<city>[\w\s]+)\s*,)?"
        r"\s*((?P<state>[\w\s]+)\s*,)?"
        r"\s*((?P<zip>\w?\d\d\d\d(\w\w\w)?)\s*,)?"
        r"\s*(?P<country>[Aa]rgentina)", re.UNICODE),
]

street2_searcher = {
    'argentina': [
        re.compile('(piso\s+\w+)'),
        re.compile('(dpto.[^,]*)'),
    ]
}


def strip_accents(s):
    return ''.join((c for c in unicodedata.normalize('NFD', s)
                    if unicodedata.category(c) != 'Mn'))


def _st(i, s=' ', m='+'):
    i = i.lower()
    i = m.join(i.split(s))
    i = i.encode('ascii', 'xmlcharrefreplace')
    return i


def search_zip(street, number, city, state, country, unique=True):
    """
    Return zipcode. Only works with argentina.

    >>> search_zip("rivadavia", "9800", "buenos aires",
                   "capital federal", "argentina")
    u'C1407DZT'
    >>> search_zip("jose clemente paz", "1200",
                   "jose clemente paz", "buenos aires", "argentina")
    u'B1665BBB'
    >>> search_zip("general paz", "5445",
                   "general san martin", "buenos aires", "argentina")
    u'1650'
    """
    street = strip_accents(street.lower())
    city = strip_accents(city.lower())
    state = strip_accents(state.lower())
    country = strip_accents(country.lower())

    codpos = None

    if country in ['argentina', 'ar']:

        # Elimina titulos de calles y avidas
        street = re.sub('\s*av\s+', '', street)

        re_cpa = re.compile('>(\w{8})<')

        if state in ['capital federal']:
            codloca = ['5001']
            codpos = ['']
        else:
            url = "http://www3.correoargentino.com.ar/scriptsN/cpa/' \
                'cpa_loca.idc?codprov=%s&pnl=%s"
            inpage = urlopen(url % (codprov_dict[country][state], _st(city)))
            soup = BeautifulSoup(inpage)
            options = soup.findAll('option')
            if len(options) == 0:
                raise RuntimeError('No locations for "%s"' % ','.join(
                    [street, number, city, state, country]))

            loca = map(
                lambda opt: re.search('(.*)\s*\(\d+\)',
                                      opt.string.lower()).groups()[0].strip(),
                options)
            codloca = map(
                lambda opt: opt['value'],
                options)
            codpos = map(
                lambda opt: re.search('\((\d+)\)',
                                      opt.string).groups()[0],
                options)

        for i in xrange(len(codloca)):
            url = 'http://www3.correoargentino.com.ar/scriptsN/cpa/' \
                  'cpa_calle.idc?codloca=%s&pnc=%s&alt=%s'
            inpage = urlopen(url % (codloca[i], _st(street), number))
            soup = BeautifulSoup(inpage)
            output = soup.body.div.table.tr.td.renderContents()
            match = re_cpa.search(output)
            if match:
                codpos[i] = match.group(1)

        if len(codloca) > 1 and unique:
            i = mostequivalent(loca, city)
            return codpos[i]
        else:
            return unicode(codpos[0])
    else:
        raise NotImplementedError


def unify_geo_data(input_string):
    """
    Return unified geographic data

    >>> data = unify_geo_data("Av. rivadavia 9858, buenos aires, argentina")
    >>> data == {'latitud': -34.637979199999997, 'city': u'Buenos Aires',\
                 'country': u'Argentina', 'number': u'9858',\
                 'state': u'Capital Federal',\
                 'street': u'Av Rivadavia', 'street2': '',\
                 'longitud': -58.503058099999997, 'zip': 'C1407DZU'}
    True
    >>> data = unify_geo_data("gral paz 9858, general san martin,
                              buenos aires, argentina")
    >>> data == {'latitud': -34.581238599999999, 'city': '', 'zip': '',\
                 'country': u'Argentina', 'number': u'9858',\
                 'state': u'Buenos Aires', 'street': u'Gral. Paz',\
                 'street2': '', 'longitud': -58.513873400000001}
    True
    >>> data = unify_geo_data("VICTORIA OCAMPO 360 PISO PB,
                              CAPITAL FEDERAL,CAPITAL FEDERAL,Argentina")
    >>> data == {'latitud': -34.601967000000002, 'city': u'Buenos Aires',\
                 'zip': '', 'country': u'Argentina', 'street2': 'piso pb',\
                 'number': u'360', 'state': u'Capital Federal',\
                 'street': u'Victoria Ocampo', 'longitud': -58.364093699999998}
    True
    >>> data = unify_geo_data("AV. DEL LIBERTADOR 767 PISO 1,
                              VICENTE LOPEZ,BUENOS AIRES,Argentina")
    >>> data == {'latitud': -34.527026800000002, 'city': u'Vicente L\xf3pez',\
                 'zip': u'1638', 'country': u'Argentina', 'street2': 'piso 1',\
                 'number': u'767', 'state': u'Buenos Aires Province',\
                 'street': u'Av Del Libertador Gral. San Martin',\
                 'longitud': -58.471314999999997}
    True
    >>> data = unify_geo_data("PELLEGRINI 255,,,SANTA ROSA,LA PAMPA,Argentina")
    >>> data == {'latitud': -36.619441799999997, 'city': u'Santa Rosa',\
                 'zip': u'L6300DRE', 'country': u'Argentina', 'street2': '',\
                 'number': u'255', 'state': u'La Pampa', \
                 'street': u'Pellegrini',\
                 'longitud': -64.292496499999999}
    True
    """
    input_string = input_string.lower()
    # Remove sporius data for search and store it in street2
    street2 = []
    for country in street2_searcher.keys():
        if country in input_string:
            for rexp in street2_searcher[country]:
                match = rexp.search(input_string)
                if match:
                    street2.append(','.join(match.groups()))
                    input_string = rexp.sub('', input_string)
    street2 = ','.join(street2)
    input_string = input_string.encode('ascii', 'ignore')

    # Search data in geographics database
    try:
        _gc = geocode(_st(input_string, " ", " "))
        if _gc is None:
            return {'error': 'No geocoding service available'}
        if not _gc:
            return {'error': 'No answer'}
    except GeocoderTimedOut:
        return {'error': 'Connection timeout'}

    if len(_gc) > 1:
        i = mostequivalent(map(lambda (a, b): a, _gc), input_string)
        _gc = _gc[i]
    else:
        _gc = _gc[0]
    place, lat, lng = [_gc[k] for k in ['display_name', 'lat', 'lon']]
    _logger.debug("PLACE: %s" % place)

    for _re in address_re:
        result = _re.search(place)
        if result:
            result = result.groupdict()
            break
        _logger.debug("IGNORE: %s" % _re)

    if not result:
        return False

    _logger.debug("RESULT: %s" % result)

    data = {
        'country': result['country'],
        'zip': result['zip'],
        'state': result['state'],
        'city': result['city'],
        'nbhd': result['nbhd'],
        'number': result['number'],
        'street': result['street'],
        'street2': result['building'],
        'latitud': float(lat),
        'longitud': float(lng),
    }
    return data


def test_suite():
    import doctest
    return doctest.DocTestSuite()

if __name__ == "__main__":
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(test_suite())

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
