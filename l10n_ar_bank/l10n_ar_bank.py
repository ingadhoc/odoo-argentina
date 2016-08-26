# -*- coding: utf-8 -*-
from openerp import fields, models, api


class Bank(models.Model):
    _inherit = 'res.bank'

    bcra_code = fields.Char('BCRA Code',
                            size=8,
                            help="Code assigned by BCRA")
    vat = fields.Char('VAT',
                      size=32,
                      help="Value Added Tax number.")


class partner_bank(models.Model):
    _name = 'res.partner.bank'
    _inherit = 'res.partner.bank'

    @api.multi
    def is_valid_cbu(self):
        self.ensure_one()

        cbu = self.acc_number

        if type(cbu) == int:
            cbu = "%022d" % cbu
        cbu = cbu.strip()
        if len(cbu) != 22:
            return False
        s1 = sum(int(a)*b for a, b in zip(cbu[0:7], (7, 1, 3, 9, 7, 1, 3)))
        d1 = (10 - s1) % 10
        if d1 != int(cbu[7]):
            return False
        s2 = sum(int(a)*b
                 for a, b in zip(cbu[8:-1],
                                 (3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3)))
        d2 = (10 - s2) % 10
        if d2 != int(cbu[-1]):
            return False

        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
