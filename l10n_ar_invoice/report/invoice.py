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
import time, re
from openerp.report import report_sxw
import openerp.report.interface
import logging

_logger = logging.getLogger(__name__)

_re_ar_vat = re.compile('ar(\d\d)(\d*)(\d)')

class ar_account_invoice(report_sxw.rml_parse):

    def _is_class(self, o, cls):
        r = o.journal_id.journal_class_id.document_class_id.name in cls
        return r
    
    def _flatdate(self, d):
        f = d.replace('-', '')
        return f

    def _cuit_format(self, c):
	    cuit_string = '{0}-{1}-{2}'.format(c[:2], c[2:-1], c[-1])
        return cuit_string

    def __init__(self, cr, uid, name, context):
        super(ar_account_invoice, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'flatdate': self._flatdate,
            'is_class': self._is_class,
            'cuit_format': self._cuit_format,
            'copies': ['ORIGINAL','DUPLICADO','TRIPLICADO'],
        })

def publish_account_invoice():
    openerp.report.interface.report_int.remove('report.account.invoice')

    report_sxw.report_sxw(
        'report.account.invoice',
        'account.invoice',
        'addons/l10n_ar_wsafip/report/invoice.rml',
        parser=ar_account_invoice,
        header=False
    )

publish_account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
