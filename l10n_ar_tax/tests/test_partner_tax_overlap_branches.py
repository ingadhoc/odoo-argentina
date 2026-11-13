from odoo.exceptions import ValidationError
from odoo.tests import common, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPartnerTaxOverlapBranches(common.TransactionCase):
    """Two taxes of the same group on a partner only conflict when one company can see both lines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        country_ar = cls.env.ref("base.ar")
        cls.parent_company = cls.env["res.company"].create(
            {"name": "Padre test", "country_id": country_ar.id, "currency_id": cls.env.ref("base.ARS").id}
        )
        cls.branch_1 = cls.env["res.company"].create({"name": "Hija 1 test", "parent_id": cls.parent_company.id})
        cls.branch_2 = cls.env["res.company"].create({"name": "Hija 2 test", "parent_id": cls.parent_company.id})
        cls.tax_group = cls.env["account.tax.group"].create(
            {"name": "IIBB test", "country_id": country_ar.id, "company_id": cls.parent_company.id}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Contacto test"})
        cls.tax_parent = cls._create_tax(cls.parent_company)
        cls.tax_branch_1 = cls._create_tax(cls.branch_1)
        cls.tax_branch_2 = cls._create_tax(cls.branch_2)

    @classmethod
    def _create_tax(cls, company):
        return cls.env["account.tax"].create(
            {
                "name": "P. IIBB test %s" % company.name,
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 3.0,
                "country_id": cls.env.ref("base.ar").id,
                "tax_group_id": cls.tax_group.id,
                "company_id": company.id,
            }
        )

    def _create_partner_tax(self, tax):
        return self.env["l10n_ar.partner.tax"].create({"partner_id": self.partner.id, "tax_id": tax.id})

    def test_sibling_branches_do_not_conflict(self):
        self._create_partner_tax(self.tax_branch_1)
        self._create_partner_tax(self.tax_branch_2)
        self.assertEqual(len(self.partner.l10n_ar_partner_perception_ids), 2)

    def test_parent_and_branch_conflict(self):
        self._create_partner_tax(self.tax_branch_1)
        with self.assertRaises(ValidationError):
            self._create_partner_tax(self.tax_parent)

    def test_branch_and_parent_conflict(self):
        self._create_partner_tax(self.tax_parent)
        with self.assertRaises(ValidationError):
            self._create_partner_tax(self.tax_branch_1)

    def test_conflict_does_not_depend_on_selected_companies(self):
        # the branch line is hidden with only the parent selected, but the branch would see both lines
        self._create_partner_tax(self.tax_branch_1)
        user = new_test_user(
            self.env,
            login="partner_tax_overlap_user",
            groups="base.group_user,account.group_account_manager",
            company_id=self.parent_company.id,
            company_ids=[(6, 0, (self.parent_company | self.branch_1).ids)],
        )
        env = self.env(user=user, context=dict(self.env.context, allowed_company_ids=[self.parent_company.id]))
        with self.assertRaises(ValidationError):
            env["l10n_ar.partner.tax"].create({"partner_id": self.partner.id, "tax_id": self.tax_parent.id})
