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
    'author':  'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'category': 'Accounting & Finance',
    'data': [
        # 'views/account_tax_withholding_view.xml',
        # 'views/account_tax_withholding_template_view.xml',
        # 'views/account_withholding_view.xml',
        'views/account_voucher_view.xml',
        # 'data/data.xml',
        # 'security/security.xml',
        # 'security/ir.model.access.csv'
        'views/res_company_view.xml',
    ],
    'demo': [
        'demo/ir_parameter.xml',
    ],
    'depends': [
        'account_voucher_withholding',
        'l10n_ar_invoice',
    ],
    'external_dependencies': {
        'python': ['pyafipws'],
    },
    'installable': True,
    'name': 'Argentinian Withholding Management',
    'test': [],
    'version': '8.0.0.0.0',
 }
