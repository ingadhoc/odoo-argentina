from odoo.tests import Form, TransactionCase, tagged


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
        self.assertEqual(self.env["res.bank"].search([("bank_number", "=", "005")]), self.abn_amro)

    def test_partner_bank_account_exposes_bcra_code(self):
        partner = self.env["res.partner"].create({"name": "Cliente con cuenta"})
        with Form(self.env["res.partner.bank"]) as account_form:
            account_form.partner_id = partner
            account_form.acc_number = "0050001234567890123456"
            account_form.bank_id = self.abn_amro
        account = account_form.save()
        self.assertEqual(account.bank_id.bank_number, "005")
