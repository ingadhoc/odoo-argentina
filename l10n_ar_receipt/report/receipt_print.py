# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Silvina Faner (<http://tiny.be>).
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

import time
from report import report_sxw
import netsvc

class report_receipt_print(report_sxw.rml_parse):
    _name = 'report.receipt.print'
    def __init__(self, cr, uid, name, context):
        super(report_receipt_print, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'convert': self.convert,
        })

    def convert(self, amount, currency): return self.pool.get('ir.translation').amount_to_text(amount, 'pe', currency or 'Pesos')

report_sxw.report_sxw(
    'report.receipt.print',
    'receipt.receipt',
    'trunk/receipt_pay/report/receipt_pay_print.rml',
    parser=report_receipt_print,header="external"
)
