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
{   'active': False,
    'author': 'OpenERP Team de Localizacion Argentina',
    'category': 'Generic Modules/Accounting',
    'data': [   
                'account_voucher_view.xml',
                'workflow_third.xml',
                'workflow_issued.xml',
                'workflow_checkbook.xml',
                'wizard_third/view_check_deposit.xml',
                'wizard_third/view_check_hreject.xml',
                'wizard_third/view_check_dreject.xml',
                'wizard_third/view_check_sold.xml',
                # 'wizard_third/view_ticket_check_deposit.xml',
                'wizard_issued/view_issued_check_hreject.xml',
                'account_check_duo_view.xml',
                'partner_view.xml',
                'account_view.xml',
                'security/ir.model.access.csv',
                'check_third_sequence.xml',
                # 'ticket_deposit_view.xml',
                'account_checkbook_view.xml',
                'report_webkit_html_view.xml'],
    'demo': [],
    'depends': [   'account',
                   'account_voucher',
                   'report_webkit'],
    'description': '\n\n    \n\n This module provides to manage checks (issued and third) \n\n    Add models of Issued Checks and Third Checks. (Accounting/Banck ans Cash/Checks/)\n\n    Add options in Jorunals for using  checks in vouchers.\n\n    Add range of numbers for issued check (CheckBook).Accounting/configuration/Miscellaneous/CheckBooks.\n\n    Add ticket deposit for third checks. Change states from Holding to deposited.(Accounting/Banck ans Cash/Checks/)\n\n    \n\n\t\t',
    'installable': True,
    'name': 'Account Check Duo',
    'test': [],
    'version': '1.243'}
