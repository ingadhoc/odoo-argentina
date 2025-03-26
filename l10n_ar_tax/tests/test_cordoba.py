import requests
from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common
from unittest.mock import patch


class TestCordoba(common.TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.partner = self.env["res.partner"].create(
            {
                "name": "test_company",
                "l10n_latam_identification_type_id": self.env.ref("l10n_ar.it_cuit").id,
                "vat": "30697130841",
            }
        )
 
    @patch('requests.post')
    def test_timeout_exception(self, mock_post):
        date = fields.Date.today()
        to_date = fields.Date.today() + relativedelta(days=1)
        mock_post.side_effect = requests.exceptions.Timeout

        with self.assertRaises(UserError) as context:
            self.env["account.fiscal.position.l10n_ar_tax"]._get_rentas_cordoba_data(self.partner, date, to_date)

        self.assertIn("Timeout", str(context.exception))

    @patch('requests.post')
    def test_general_request_exception(self, mock_post):
        date = fields.Date.today()
        to_date = fields.Date.today() + relativedelta(days=1)
        mock_post.side_effect = requests.exceptions.RequestException("Request Exception")

        with self.assertRaises(UserError) as context:
            self.env["account.fiscal.position.l10n_ar_tax"]._get_rentas_cordoba_data(self.partner, date, to_date)

        self.assertIn("Error when contacting rentascordoba.gob.ar", str(context.exception))
