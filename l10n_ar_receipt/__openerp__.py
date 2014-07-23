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
    'author': 'OpenERP - Team de Localizaci\xc3\xb3n Argentina',
    'category': 'Accounting & Finance',
    'data': [   'receipt_view.xml',
                'account_voucher_view.xml',
                'security/ir.model.access.csv',
                'proof_view.xml',
                'receiptbook_view.xml',
                'workflow_receiptbook.xml',
                'receipt_pay_view.xml',
                'receipt_secuence.xml',
                'proof_secuence.xml',
                'report/report_view.xml'],
    'demo': [],
    'depends': ['account_voucher'],
    'description': '\n\n    This module provides some features to print receipts of invoices\n\n        It gives you the possibility to:\n\n            Print receipts of more than one vouchers (only for same clients).\n\n            Show all receipts of customer and suppliers.\n\n            Show receiptbooks.\n\n \n\n\t\t',
    'installable': True,
    'name': 'Receipt',
    'test': [],
    'version': '1.243'}
