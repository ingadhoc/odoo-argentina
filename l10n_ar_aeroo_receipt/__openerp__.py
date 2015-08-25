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
    'name': 'Argentinian Like Receipt Aeroo Report',
    'version': '8.0.1.0.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author':  'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Argentinian Like Receipt Aeroo Report
=====================================
Por defecto se utiliza el reporte "l10n_ar_aeroo_receipt/receipt.odt" que detalla los pagos en
* Cheques
* Banco
* Efectivo
Si se quiere detallar en función a los diarios se puede cambiar en configuracion/tecnico/aeroo reports/reports, ubicando el reporte "Argentinian Aeroo Receipt" en valor de template path por "l10n_ar_aeroo_receipt/receipt_journal_detail.odt"
    """,
    'depends': [
        'report_extended_voucher_receipt',
        'account_check',
        'l10n_ar_aeroo_base',
        'l10n_ar_invoice',
    ],
    'external_dependencies': {
    },
    'data': [
        'receipt_report.xml',
        'voucher_receipt_template.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
