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
    "name": "Adjust Account Follow UP for Argentinian Localization",
    'version': '9.0.1.0.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    "description": """
Adjust Account Follow UP for Argentinian Localization
=====================================================
    """,
    'depends': [
        'account_followup',
        'l10n_ar_account',
    ],
    'external_dependencies': {
    },
    'data': [
        'account_move_line_view.xml',
        'partner_view.xml',
        'wizard/account_company_followup_wizard.xml',
        'views/report_followup.xml',
        'views/customer_followup__view.xml',
        'views/account_company_select.xml',

    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': False,
    'auto_install': True,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
