from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestPartnerVatChange(TestArWithholdingArRi):
    def setUp(self):
        super().setUp()
        self.ar_partner = self.env["res.partner"].create(
            {
                "name": "Partner with aliquots",
                "country_id": self.env.ref("base.ar").id,
                "l10n_latam_identification_type_id": self.env.ref("l10n_ar.it_cuit").id,
                "l10n_ar_afip_responsibility_type_id": self.env.ref("l10n_ar.res_IVARI").id,
                "vat": "20055361682",
                "is_company": True,
            }
        )
        self.contact = self.env["res.partner"].create({"name": "Contact", "parent_id": self.ar_partner.id})
        perception = self.env.ref("account.%i_ri_tax_percepcion_iibb_caba_aplicada" % self.env.company.id)
        today = fields.Date.today()
        self.env["l10n_ar.partner.tax"].create(
            {
                "tax_id": perception.id,
                "partner_id": self.ar_partner.id,
                "company_id": self.company_ri.id,
                "from_date": today.replace(day=1),
            }
        )

    def test_vat_change_blocked_with_aliquots(self):
        with self.assertRaises(UserError):
            self.ar_partner.vat = "30714295698"
        with self.assertRaises(UserError):
            self.contact.vat = "30714295698"
        self.assertEqual(self.ar_partner.vat, "20055361682")

    def test_vat_same_digits_allowed(self):
        self.ar_partner.vat = "20-05536168-2"
        self.assertEqual(self.ar_partner.vat, "20-05536168-2")

    def test_vat_change_allowed_without_aliquots(self):
        self.ar_partner.l10n_ar_partner_perception_ids.unlink()
        self.ar_partner.vat = "30714295698"
        self.assertEqual(self.contact.vat, "30714295698")

    def test_vat_change_allowed_deleting_aliquots_in_the_same_save(self):
        aliquots = self.ar_partner.l10n_ar_partner_perception_ids
        self.ar_partner.write(
            {"vat": "30714295698", "l10n_ar_partner_perception_ids": [Command.delete(a.id) for a in aliquots]}
        )
        self.assertEqual(self.ar_partner.vat, "30714295698")
        self.assertFalse(aliquots.exists())
