# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.addons.account.tests.test_tax import TestTax


class ArTestTax(TestTax):

    def test_tax_sequence_normalized_set(self):
        # super(ArTestTax, self).test_tax_sequence_normalized_set()
        self.division_tax.sequence = 1
        self.fixed_tax.sequence = 2
        self.percent_tax.sequence = 3
        taxes_set = (self.group_tax | self.division_tax)
        res = taxes_set.compute_all(200.0)
        self.assertEquals(round(res['taxes'][0]['amount'], 2), 22.22)
        self.assertEquals(round(res['taxes'][1]['amount'], 2), 10.0)
        self.assertEquals(round(res['taxes'][2]['amount'], 2), 20.0)
