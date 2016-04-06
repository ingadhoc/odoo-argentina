# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
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
    'name': 'Retenciones para Plan Contable General Argentino',
    'version': '8.0.1.0.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author':  'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Retenciones para Plan Contable General Argentino
================================================
""",
    'depends': [
        'l10n_ar_chart_generic',
        'account_voucher_withholding',
    ],
    'external_dependencies': {
    },
    'data': [
        'data/account_chart_respinsc.xml',
    ],
    'demo': [
        # TODO enable this demo data or use it on l10n_ar_withh..
        # 'demo/ri_withholding_demo.xml',
        # 'demo/ri_voucher_demo.xml',
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
