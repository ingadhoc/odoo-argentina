# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp.osv import fields, osv
from openerp import api
import re
_re_ar_vat = re.compile('ar(\d\d)(\d*)(\d)', re.IGNORECASE)


class res_partner(osv.osv):
    _inherit = 'res.partner'

    @api.model
    def _commercial_fields(self):
        """
        Nosotros no usamos el campo vat practicamente y si se copia a los
        contactos, luego, con vat unique, si sacamos un contacto tenemos error
        y es poco claro. Preferimos que no se copie a los contactos lo relativo
        a vat
        """
        res = super(res_partner, self)._commercial_fields()
        if 'vat' in res:
            res.remove('vat')
        if 'vat_subjected' in res:
            res.remove('vat_subjected')
        return res

    def _get_formated_vat(self, cr, uid, ids, name, args, context=None):
        """
        Retorna el CUIT formateado en forma oficial (XX-XXXXXXXX-X).
        """
        res = {}
        for partner in self.browse(cr, uid, ids):
            res[partner.id] = self.format_vat_ar(partner.vat)
        return res

    _columns = {
        'formated_vat': fields.function(
            _get_formated_vat, method=True,
            string='Printeable VAT', type="char"),
    }

    def format_vat_ar(self, vat):
        cuit_parse = _re_ar_vat.match(vat) if vat else None
        cuit_string = '{0}-{1}-{2}'.format(
            *cuit_parse.groups()) if cuit_parse is not None else vat
        return cuit_string

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
