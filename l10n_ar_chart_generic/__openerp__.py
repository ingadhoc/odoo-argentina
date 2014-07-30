# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2012 OpenERP - Team de Localización Argentina.
# https://launchpad.net/~openerp-l10n-ar-localization
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Argentina - Plan Contable General',
    'version': '2.7.155',
    'author':   'OpenERP - Team de Localización Argentina',
    'category': 'Localization/Account Charts',
    'website':  'https://launchpad.net/~openerp-l10n-ar-localization',
    'license': 'AGPL-3',
    'description': """
Plan contable genérico para la Argentina.

Incluye:
  - Wizard de configuración.
  - Plantilla del plan contable genérico.

""",
    'depends': [
        'account',
        'account_chart',
        'l10n_multilang',
        # 'base_vat',
        # 'base_iban',
        # 'l10n_ar_states',
        # 'l10n_ar_base_vat',
    ],
    'init_xml': [],
    'demo_xml': [],
    'test': [],
    'update_xml': [
        'data/account_types.xml',
        'data/account_chart_respinsc.xml',
#        'data/account_chart_monotrib.xml',
#        'data/account_chart_coop.xml',
        'data/res_partner.xml',
    ],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
