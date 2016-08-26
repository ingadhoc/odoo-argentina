# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    _logger.warning("Please,"
                    " install BeautifulSoup using 'pip install beautifulsoup'.")
    BeautifulSoup = None

import re
from geosearch import unify_geo_data, strip_accents
from cache import urlopen

encoding = 'ISO-8859-1'
compiled_re = {
    'code': re.compile(r'N... Banco:\s*(\d+)'),
    'office': re.compile(r'Direcci..n:&nbsp;\s*(.{40})'),
    'street': re.compile(r'Direcci..n:&nbsp;\s*.{40}([^-]*)-'),
    'city': re.compile(r'Direcci..n:&nbsp;\s*.{40}[^-]*-([^-]*)-'),
    'state': re.compile(r'Direcci..n:&nbsp;\s*.{40}[^-]*-[^-]*-([^-]*)'),
    'phone': re.compile(r'Tel..fono:&nbsp;([\d-]+)\s*&nbsp;'),
    'fax': re.compile(r'Fax:&nbsp;([\d-]+)\s*&nbsp;'),
    'email': re.compile(r'Email:&nbsp;<a href="mailto:([^"\s]+)\s*"'),
    'address': re.compile(r'Direcci..n:&nbsp;\s*(.*)\s*\r'),
    'site': re.compile(r'Sitio:&nbsp;<a href="([^"\s]+)\s*"'),
    'gins': re.compile(r'Grupo Institucional:&nbsp;\s*(.*)\s*'),
    'ghom': re.compile(r'Grupo Homog..neo:&nbsp;\s*(.*)\s*'),
    'vat': re.compile(r'CUIT:&nbsp;([\d-]+)\s*&nbsp;'),
}


postprocessor_keys = {
    'code': lambda v, d: 'email' in d and [s for s in
                                           d['email'].split('@')[1].split('.')
                                           if s not in ["ar", "com"]
                                           ][0].upper() or v,
    'street': lambda v, d: "%(street)s %(number)s" % d,
    'name': lambda v, d: d[v].title() if d[v] else "",
    'state': lambda v, d: d[v].replace(" Province", "") if d[v] else ""
}

dictkeys = [
    'code',
    'name',
    'bic',
    'street',
    'number',
    'street2',
    'zip',
    'city',
    'state',
    'country',
    'latitud',
    'longitud',
    'phone',
    'fax',
    'email',
    'active',
    'id',
    'vat',
    'office',
    'site',
    'gins',
    'ghom',
    'address',
]

bankfields = [
    'id',
    'name',
    'code',
    'active',
    'bic',
    'street',
    'street2',
    'zip',
    'city',
    'state',
    'country',
    'phone',
    'fax',
    'email',
    'vat',
]


def ar_banks_iterator(
    url_bank_list='http://www.bcra.gov.ar/Sistema_financiero/sisfin020101.asp',
    url_bank_info='http://www.bcra.gob.ar/Sistema_financiero/'
    'sisfin020101.asp?bco=%s',
    country='Argentina'
):
    """
    Argentinian Banks list iterator.

    >>> banks = ar_banks_iterator()
    >>> banks.next().keys() == ['latitud', 'ghom', 'fax', 'code', 'office', \
                                'street2', 'site', 'number', 'phone', \
                                'street', 'address', 'active', 'gins', 'id', \
                                'longitud', 'city', 'name', 'zip', 'country', \
                                'state', 'email', 'vat']
    True
    """
    if BeautifulSoup is None:
        return

    page_list = urlopen(url_bank_list)
    soup_list = BeautifulSoup(page_list)

    for bank in soup_list('option'):
        if 'value' in dict(bank.attrs):
            id, name = bank['value'].strip(), bank.string.strip()
            page_bank = urlopen(url_bank_info % id)
            soup_bank = BeautifulSoup(page_bank)

            data = {
                'id': id,
                'bcra_code': id,
                'name': name,
                'country': country,
                'active': '1',
                'number': '',
            }
            for line in soup_bank(id='texto_columna_2')[0]('table')[1]('tr'):
                sline = line.td.renderContents()
                for key in compiled_re.keys():
                    search = compiled_re[key].search(sline)
                    if search:
                        data[key] = unicode(search.group(1).strip(), encoding)
            searchaddress = u"%(street)s, %(city)s, %(state)s, %(country)s" \
                % data
            geodata = unify_geo_data(strip_accents(searchaddress))
            if geodata:
                data.update(geodata)
                for key in postprocessor_keys.keys():
                    if key in data:
                        data[key] = postprocessor_keys[key](key, data)
                        data[key] = data[key]
            else:
                _logger.warning("No geoposition %s." % (searchaddress))
            yield data

    return

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
