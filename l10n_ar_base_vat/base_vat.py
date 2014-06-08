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

from openerp.osv import fields, osv
import re

_re_ar_vat = re.compile('ar(\d\d)(\d*)(\d)')

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _get_printed_vat(self, cr, uid, ids, prop, unknown_non, unknow_dict):
        """
        Retorna el CUIT formateado en forma oficial (XX-XXXXXXXX-X).
        """
        res = {}
        for partner in self.browse(cr, uid, ids):
            res[partner.id] = self.format_vat_ar(partner.vat)
        return res

    _columns = {
        'printed_vat': fields.function(_get_printed_vat, method=True, string='Printeable VAT', type="string",
                                       store=False),
    }

    def format_vat_ar(self, vat):
        cuit_parse = _re_ar_vat.match(vat) if vat else None
        cuit_string = '{0}-{1}-{2}'.format(*cuit_parse.groups()) if cuit_parse is not None else vat
        return cuit_string

#    # La opción que estoy viendo es:
#    def check_vat_dni(self, vat):
#        pass
#
    # La opción que estoy viendo es:
    #def check_vat_ci(self, vat):
    #    pass
#
#    # La opción que estoy viendo es:
#    def check_vat_pass(self, vat):
#        pass

    def check_vat_ar(self, vat):
        """
        Check VAT (CUIT) for Argentina
        """
        cstr = str(vat)
        salt = str(5432765432)
        n = 0
        sum = 0

        if not vat.isdigit:
            return False

        if (len(vat) != 11):
            return False

        while (n < 10):
            sum = sum + int(salt[n]) * int(cstr[n])
            n = n + 1

        op1 = sum % 11
        op2 = 11 - op1

        code_verifier = op2

        if (op2 == 11 or op2 == 10):
            if (op2 == 11):
                code_verifier = 0
            else:
                code_verifier = 9

        if (code_verifier == int(cstr[10])):
            return True
        else:
            return False

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
