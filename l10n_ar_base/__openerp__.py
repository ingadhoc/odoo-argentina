# -*- coding: utf-8 -*-
##############################################################################
#
#    Sistemas ADHOC - ADHOC SA
#    https://launchpad.net/~sistemas-adhoc
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Argentinian Localization',
    'version': '1.0',
    'category': 'Argentinian Localization',
    'sequence': 14,
    'summary': 'localization, argentina, configuration',
    'description': """
Provides the configuration for whole business suite according to Argentinian Localization.
==========================================================================================
Here, you can configure the whole business suite based on your requirements. You'll be provided different configuration options in the Settings where by only selecting some booleans you will be able to install several modules and apply access rights in just one go.

Features
+++++++++++++++
Product Features
--------------------
TODO


Warehouse Features
------------------------
TODO

Sales Features
--------------------
TODO

* TODO1
* TODO2
* TODO3

Purchase Features
-------------------------
TODO

* TODO1
* TODO2

Finance Features
------------------
TODO

Extra Tools
-------------
TODO

* TODO1
* TODO2
    """,
    'author':  'Sistemas ADHOC',
    'website': 'www.sistemasadhoc.com.ar',
    'images': [
    ],
    'depends': [
        'base_setup'
    ],
    'data': [
        'l10n_ar_base_groups.xml',
        'res_config_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: