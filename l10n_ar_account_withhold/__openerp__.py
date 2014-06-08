# -*- coding: utf-8 -*-
##############################################################################
#
#    school module for OpenERP
#    Copyright (C) 2010 Tecnoba S.L. (http://www.tecnoba.com)
#       Pere Ramon Erro Mas <pereerro@tecnoba.com> All Rights Reserved.
#    Copyright (C) 2011 Zikzakmedia S.L. (http://www.zikzakmedia.com)
#       Jesús Martín Jiménez <jmargin@zikzakmedia.com> All Rights Reserved.
#
#    This file is a part of school module
#
#    school OpenERP module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    school OpenERP module is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Módulo de retenciones de ganancias de la República Argentina.',
    'version': '0.1.1',
    'author': 'Team de Localización Argentina.',
    'website': 'https://launchpad.net/~openerp-l10n-ar-localization',
    'description': """
El modulo esta en desarrollo y no aporta funcionalidad por el momento, sirve para ver campos y configuraciones que luego serían utilizadas

    """,
    "category": "Localization/Argentina",
    "depends": [
        'account_voucher_receipt',
        ],
    'update_xml': [
        'account_view.xml',
        'res_partner_view.xml',
        # 'account_data.xml',
    ],
    'demo_xml': [],
    'active': False,
    'installable': True,
    'application': True,
}
