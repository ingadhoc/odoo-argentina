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

import time
from openerp.report import report_sxw
from openerp.addons.l10n_ar_invoice.report.invoice import ar_account_invoice

class fex_account_invoice(ar_account_invoice):

    def _is_export_electronic(self, o):
        r = True if o.journal_id.afip_authorization_id else False
        return r
    
    def __init__(self, cr, uid, name, context):
        super(fex_account_invoice, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'is_export_electronic': self._is_export_electronic,
        })

report_sxw.report_sxw(
    'report.account.invoice_fex',
    'account.invoice',
    'addons/l10n_ar_wsafip_fex/report/invoice.rml',
    parser=fex_account_invoice,
    header=False
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
