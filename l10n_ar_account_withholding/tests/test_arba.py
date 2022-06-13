from odoo.tests import common
from odoo.exceptions import UserError
import pprint

class TestARBA(common.TransactionCase):
    def test_0_arbaconnect(self):
        partner = self.env['res.partner'].create({'name': 'test_company','l10n_latam_identification_type_id': self.env.ref('l10n_ar.it_cuit').id,'vat':'30697130841'})
        company = self.env['res.company'].create({'name': 'test_company','partner_id': partner.id,'vat':'30697130841'})
        self.env.company = company
        with self.assertRaisesRegex(UserError, 'You must configure CIT'):
            self.env.company.arba_connect()
        company.vat = ''
        with self.assertRaisesRegex(UserError, 'No VAT configured'):
            self.env.company.arba_connect()

