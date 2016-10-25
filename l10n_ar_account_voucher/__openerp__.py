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
    'name': 'Aregentinian Receipts and Payment Orders',
    'version': '8.0.1.3.2',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author':  'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Aregentinian Receipts and Payment Orders
========================================
    """,
    'depends': [
        'l10n_ar_invoice',
        'account_voucher',
    ],
    'external_dependencies': {
    },
    'data': [
        'security/account_voucher_receipt_security.xml',
        'security/ir.model.access.csv',
        'views/account_voucher_view.xml',
        'views/account_voucher_receiptbook_view.xml',
        # now we create receips on chart installation if argentinian cia
        # 'data/receipt_data.xml',
    ],
    'demo': [
        'data/receipt_demo.xml',
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
