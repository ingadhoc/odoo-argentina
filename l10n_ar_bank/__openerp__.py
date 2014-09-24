# -*- coding: utf-8 -*-

{   'active': False,
    'author': 'OpenERP - Team de Localizaci\xc3\xb3n Argentina',
    'category': 'Localization/Argentina',
    'demo': [],
    'depends': ['base', 'l10n_ar_states'],
    'description': '\n\nBanks of Argentina\n\n==================\n\n\n\nSpanish\n\n-------\n\n\n\nListado de entidades financieras habilitadas por el BCRA.\n\n\n\nEste m\xc3\xb3dulo le permite tener a disposici\xc3\xb3n el listado actualizado de\n\nlas entidades bancarias de la Rep\xc3\xbablica Argentina.\n\n\n\nIncluye:\n\n - Entidades financieras (http://www.bcra.gov.ar/)\n\n - Asistente de actualizaci\xc3\xb3n de bancos.\n\n\n\nRequiere:\n\n\tBeautifulSoup\n\n\tgeopy\n\n\n\nPara que el asistente funcione debe tener instalada ambos m\xc3\xb3dulos de python.\n\n\n\nInstalaci\xc3\xb3n de los requerimientos:\n\n\n\n\t$ pip install BeautifulSoup\n\n\t$ pip install geopy\n\n\n\nejecutar desde la linea de comandos.\n\n\n\nEnglish\n\n-------\n\n\n\nIncludes:\n\n - Financial Entities (http://www.bcra.gov.ar/)\n\n - A wizard online updater.\n\n\n\nRequires:\n\n\tBeautifulSoup\n\n\tgeopy\n\n\n\nAttention, to run the wizard you need to have installed two libraries in python.\n\nWithout these two libraries the wizard will fail and will not update the information.\n\n\n\nInstall them using:\n\n\n\n\t$ pip install BeautifulSoup\n\n\t$ pip install geopy\n\n\n\nfrom the CLI.\n\n\n\n',
    'external_dependencies': {   'python': ['BeautifulSoup', 'geopy']},
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Banks of Argentina',
    'test': ['test/l10n_ar_banks_wizard.yml'],
    'data': [   'data/res_bank.xml',
                      'l10n_ar_bank.xml',
                      'l10n_ar_bank_menu.xml',
                      'wizard/wiz_l10n_ar_bank.xml'],
    'version': '2.7.243',
    'website': 'https://launchpad.net/~openerp-l10n-ar-localization'}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
