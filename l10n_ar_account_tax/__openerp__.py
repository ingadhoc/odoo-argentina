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
    'author': 'Hernan Diego Broun (HDB)',
    'website': 'http://www.elepeservicios.com.ar',
    'description': """Test de funcionalidades varias.
    1. Manejo de eventos: on_change.
    2. Calculos entre campos.
    3. Manejo de MVC.
    4. Grabacion a DB por lote.
    """,
    "category": "Apps",
    "depends": ['base', 'account', 'account_voucher', 'account_accountant', 'l10n_ar_chart_generic'],
    'update_xml': [
    'retenciones_view.xml',
    # 'retenciones_data.xml'
    ],
    'demo_xml': [],
    'active': False,
    'installable': True,
    'application': True,
}
