import base64
from unittest import mock

import requests
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestSameCuitBranches(common.TransactionCase):
    """A branch with the same CUIT as its parent uses the parent's CIT when it has none of its
    own; a branch with another CUIT never does. The padron is the same for every taxpayer, so
    any company uses the one another company uploaded, whatever its CUIT.

        root            CUIT 30697130841  CIT + ARBA padron
          ├─ branch     CUIT 30697130841
          │    └─ sub_branch  CUIT 30697130841
          └─ other_cuit CUIT 30500010084
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cuit_type = cls.env.ref("l10n_ar.it_cuit")
        cls.root = cls._create_company("Root", "30697130841")
        cls.branch = cls._create_company("Branch", "30697130841", parent=cls.root)
        cls.sub_branch = cls._create_company("Sub Branch", "30697130841", parent=cls.branch)
        cls.other_cuit = cls._create_company("Other CUIT", "30500010084", parent=cls.root)
        cls.root.arba_cit = "root_cit"
        cls.state_arba = cls.env.ref("base.state_ar_b")
        cls.today = fields.Date.today()

    @classmethod
    def _create_company(cls, name, cuit, parent=None):
        company = cls.env["res.company"].create({"name": name, "parent_id": parent.id if parent else False})
        company.partner_id.write({"l10n_latam_identification_type_id": cls.cuit_type.id, "vat": cuit})
        return company

    def _create_padron(self, company):
        return self.env["res.company.jurisdiction.padron"].create(
            {
                "company_id": company.id,
                "state_id": self.state_arba.id,
                "file_padron": base64.b64encode(b"padron"),
                "filename": "padron.zip",
                "l10n_ar_padron_from_date": fields.Date.start_of(self.today, "month"),
                "l10n_ar_padron_to_date": fields.Date.end_of(self.today, "month"),
            }
        )

    def _search_padron(self, company):
        fiscal_position = self.env["account.fiscal.position"].create({"name": "FP", "company_id": company.id})
        fp_tax = self.env["account.fiscal.position.l10n_ar_tax"].new({"fiscal_position_id": fiscal_position.id})
        return fp_tax._search_padron_file(self.state_arba, self.today)

    def _arba_consultar(self, company):
        return company.arba_consultar_contribuyente(
            "30697130841", fields.Date.start_of(self.today, "month"), fields.Date.end_of(self.today, "month")
        )

    @mute_logger("odoo.addons.l10n_ar_tax.models.res_company")
    def _get_cit_sent(self, company):
        with mock.patch.object(requests, "post", side_effect=requests.exceptions.Timeout()) as post:
            with self.assertRaisesRegex(UserError, "ARBA webservice"):
                self._arba_consultar(company)
        return post.call_args.kwargs["data"]["password"]

    def test_cit_shared_down_the_fiscal_entity(self):
        self.assertEqual(self._get_cit_sent(self.sub_branch), "root_cit")
        branch_user = new_test_user(
            self.env, "sub_branch_user", company_id=self.sub_branch.id, company_ids=self.sub_branch.ids
        )
        self.assertEqual(
            self._get_cit_sent(self.sub_branch.with_user(branch_user)),
            "root_cit",
            "A user without access to the parent company still uses its CIT",
        )
        self.branch.arba_cit = "branch_cit"
        self.assertEqual(self._get_cit_sent(self.sub_branch), "branch_cit", "The nearest CIT wins")
        with self.assertRaisesRegex(UserError, "You must configure CIT"):
            self._arba_consultar(self.other_cuit)

    def test_padron_shared_with_every_company(self):
        self.assertFalse(self._search_padron(self.sub_branch))
        root_padron = self._create_padron(self.root)
        self.assertEqual(self._search_padron(self.sub_branch), root_padron)
        self.assertEqual(self._search_padron(self.other_cuit), root_padron, "The padron does not depend on the CUIT")
        other_padron = self._create_padron(self.other_cuit)
        self.assertEqual(self._search_padron(self.other_cuit), other_padron, "The company's own padron wins")
