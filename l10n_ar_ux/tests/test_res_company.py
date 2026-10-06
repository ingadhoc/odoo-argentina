from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestInvoiceTaxCompanyCurrency(common.TransactionCase):
    """Argentinian companies must not print the taxes in company currency box on the invoice report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ar_company = cls.env["res.company"].create(
            {"name": "AR company", "country_id": cls.env.ref("base.ar").id, "currency_id": cls.env.ref("base.ARS").id}
        )
        cls.us_company = cls.env["res.company"].create(
            {"name": "US company", "country_id": cls.env.ref("base.us").id, "currency_id": cls.env.ref("base.USD").id}
        )
        cls.chart_template = cls.env["account.chart.template"]
        cls.chart_template.try_loading("ar_ri", company=cls.ar_company, install_demo=False)
        cls.chart_template.try_loading("generic_coa", company=cls.us_company, install_demo=False)

    def test_chart_template_disables_setting_only_for_ar(self):
        self.assertFalse(self.ar_company.display_invoice_tax_company_currency)
        self.assertTrue(self.us_company.display_invoice_tax_company_currency)

    def test_migration_disables_setting_only_for_ar(self):
        (self.ar_company | self.us_company).write({"display_invoice_tax_company_currency": True})
        self.env["res.company"]._l10n_ar_ux_hide_invoice_tax_company_currency()
        self.assertFalse(self.ar_company.display_invoice_tax_company_currency)
        self.assertTrue(self.us_company.display_invoice_tax_company_currency)
