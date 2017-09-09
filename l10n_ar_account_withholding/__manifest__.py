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
    'author': 'ADHOC SA,Odoo Community Association (OCA)',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'category': 'Accounting & Finance',
    'data': [
        'reports/certificado_de_retencion_report.xml',
        'views/account_payment_group_view.xml',
        'views/res_company_view.xml',
        'views/afip_tabla_ganancias_escala_view.xml',
        'views/afip_tabla_ganancias_alicuotasymontos_view.xml',
        'views/account_payment_view.xml',
        'views/res_partner_view.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/tabla_ganancias_data.xml',
    ],
    'demo': [
        'demo/ir_parameter.xml',
        # 'demo/demo.xml',
    ],
    'depends': [
        'account_withholding_automatic',
        'l10n_ar_account',
        # para ganancias
        # deberiamos requerir l10n_ar_aeroo_base pero preferimos no hacerlo
        # para no sumar dependencinas. Se deberia requerir porque el reporte
        # usa las lineas
        # 'l10n_ar_aeroo_base',
        'report_aeroo',
    ],
    'external_dependencies': {
        'python': ['pyafipws'],
    },
    'installable': False,
    'name': 'Automatic Argentinian Withholdings on Payments',
    'test': [],
    'version': '9.0.1.8.0',
}
