import base64

from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.tests import common


class TestPadronCleanupCron(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.padron_model = cls.env["res.company.jurisdiction.padron"]
        cls.state_arba = cls.env.ref("base.state_ar_b")
        cls.state_santa_fe = cls.env.ref("base.state_ar_s")
        cls.company = cls.env.company
        cls.dummy_file = base64.b64encode(b"dummy padron").decode()

    def _create_padron(self, state, to_date):
        return self.padron_model.create(
            {
                "company_id": self.company.id,
                "state_id": state.id,
                "file_padron": self.dummy_file,
                "filename": "padron.txt",
                "l10n_ar_padron_from_date": to_date + relativedelta(days=-30),
                "l10n_ar_padron_to_date": to_date,
            }
        )

    def test_cron_deletes_only_old_padrons(self):
        """Create 2 old and 2 new padrones, then verify the cron deletes only the 2 old ones."""
        threshold_date = fields.Date.start_of(fields.Date.context_today(self.padron_model), "month") + relativedelta(
            years=-1
        )

        old_arba = self._create_padron(self.state_arba, threshold_date + relativedelta(days=-1))
        old_santa_fe = self._create_padron(self.state_santa_fe, threshold_date + relativedelta(days=-10))
        new_arba = self._create_padron(self.state_arba, threshold_date + relativedelta(days=1))
        new_santa_fe = self._create_padron(self.state_santa_fe, threshold_date + relativedelta(days=30))

        self.padron_model._cron_clean_old_padron_files()

        self.assertFalse(old_arba.exists())
        self.assertFalse(old_santa_fe.exists())
        self.assertTrue(new_arba.exists())
        self.assertTrue(new_santa_fe.exists())
