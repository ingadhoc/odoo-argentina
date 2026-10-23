from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountPaymentPartnerVat(TestArCommon):
    """The CUIT shown on payments is the compact CUIT, only when the partner is identified by it."""

    def _create_payment(self, partner):
        return self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": partner.id,
                "amount": 100.0,
                "company_id": self.company_ri.id,
            }
        )

    def test_partner_with_cuit(self):
        partner = self.res_partner_adhoc.copy({"vat": "30-71429569-8"})
        self.assertEqual(self._create_payment(partner).l10n_ar_partner_vat, "30714295698")

    def test_partner_with_dni_only(self):
        partner = self.env["res.partner"].create(
            {
                "name": "DNI partner",
                "country_id": self.env.ref("base.ar").id,
                "additional_identifiers": {"AR_DNI": "28580910"},
            }
        )
        self.assertFalse(self._create_payment(partner).l10n_ar_partner_vat)

    def test_without_partner(self):
        self.assertFalse(self._create_payment(self.env["res.partner"]).l10n_ar_partner_vat)
