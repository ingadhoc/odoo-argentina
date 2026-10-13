from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountMoveSequencePos(TestArCommon):
    """The POS of a new document name always comes from the journal, not from the last name."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls._create_journal("preprinted", data={"l10n_ar_afip_pos_number": 3})

    def _post_invoice(self):
        invoice = self._create_invoice_ar(partner_id=self.res_partner_adhoc, journal_id=self.journal)
        self._post(invoice)
        return invoice

    def test_stale_pos_prefix_does_not_propagate(self):
        first = self._post_invoice()
        self.assertEqual(first.name, "FA-A 00003-00000001")

        # Name generated with the POS the journal had before
        self.env.cr.execute(
            "UPDATE account_move SET name = %s, sequence_prefix = %s WHERE id = %s",
            ("FA-A 00002-00000001", "FA-A 00002-", first.id),
        )
        first.invalidate_recordset(["name", "sequence_prefix"])

        second = self._post_invoice()
        self.assertEqual(second.name, "FA-A 00003-00000002")
        third = self._post_invoice()
        self.assertEqual(third.name, "FA-A 00003-00000003")
