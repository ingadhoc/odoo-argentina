from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestL10nArBank(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.abn_amro = cls.env.ref("l10n_ar_bank.00005")
        cls.module_banks = cls.env["res.bank"].browse(
            cls.env["ir.model.data"]
            .search([("module", "=", "l10n_ar_bank"), ("model", "=", "res.bank")])
            .mapped("res_id")
        )

    def test_catalog_has_bcra_code(self):
        self.assertEqual(self.abn_amro.name, "Abn  Amro Bank N. V.")
        self.assertEqual(self.abn_amro.bank_number, "005")
        self.assertEqual(self.abn_amro.country, self.env.ref("base.ar"))
        self.assertGreater(len(self.module_banks), 80)
        self.assertFalse(self.module_banks.filtered(lambda b: not b.bank_number))

    def test_search_by_bcra_code(self):
        galicia = self.env.ref("l10n_ar_bank.00007")
        self.assertEqual(self.env["res.bank"].search([("bank_number", "=", "007")]), galicia)

    def test_partner_bank_account_takes_bcra_code(self):
        partner = self.env["res.partner"].create(
            {"name": "Cliente con cuenta", "country_id": self.env.ref("base.ar").id}
        )
        account = self.env["res.partner.bank"].create(
            {"partner_id": partner.id, "account_number": "0050001234567890123456", "bank_id": self.abn_amro.id}
        )
        self.assertEqual(account.clearing_number, "005")
        self.assertEqual(account.clearing_label_id, self.env.ref("l10n_ar_bank.clearing_label_ar"))
        self.abn_amro.bank_number = "006"
        self.assertEqual(account.clearing_number, "006")
        account.bank_id = False
        self.assertFalse(account.clearing_number)
