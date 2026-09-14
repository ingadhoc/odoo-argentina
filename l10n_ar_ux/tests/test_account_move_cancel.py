import time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged

AFIP_AUTH_FIELDS = (
    # Enterprise (l10n_ar_edi)
    ("l10n_ar_afip_auth_mode", "l10n_ar_afip_auth_code"),
    # Community (l10n_ar_afipws_fe, odoo-argentina-ce)
    ("afip_auth_mode", "afip_auth_code"),
)


@tagged("-at_install", "post_install")
class TestAccountMoveCancel(AccountTestInvoicingCommon):
    """``button_cancel`` sobre comprobantes de venta ya confirmados.

    El override de este módulo bloquea la cancelación de un comprobante que AFIP ya
    autorizó, pero los campos de autorización se llaman distinto según la variante de
    localización instalada: ``l10n_ar_afip_auth_mode``/``l10n_ar_afip_auth_code`` en
    Enterprise (``l10n_ar_edi``) y ``afip_auth_mode``/``afip_auth_code`` en Community
    (``l10n_ar_afipws_fe``, de odoo-argentina-ce). Como ``l10n_ar_ux`` no depende de
    ninguno de los dos, leer el nombre de Enterprise a ciegas rompía con
    ``AttributeError`` en toda instalación que no fuera Enterprise.
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template("ar_ri")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.write(
            {
                "l10n_ar_afip_start_date": time.strftime("%Y-01-01"),
                "l10n_ar_gross_income_type": "local",
                "l10n_ar_gross_income_number": "901-21885123",
            }
        )
        cls.company.partner_id.write(
            {
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_cuit").id,
                "vat": "30111111118",
                "country_id": cls.env.ref("base.ar").id,
            }
        )
        cls.partner_ar = cls.env["res.partner"].create(
            {
                "name": "Cliente Consumidor Final",
                "country_id": cls.env.ref("base.ar").id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_CF").id,
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_Sigd").id,
            }
        )
        # Talonario preimpreso: no usa webservice, así que nunca lleva CAE.
        cls.preprinted_journal = cls.env["account.journal"].create(
            {
                "name": "Ventas Preimpreso (Unit Tests)",
                "type": "sale",
                "code": "PREUT",
                "company_id": cls.company.id,
                "l10n_latam_use_documents": True,
                "l10n_ar_afip_pos_number": 99,
                "l10n_ar_afip_pos_system": "II_IM",
                "l10n_ar_afip_pos_partner_id": cls.company.partner_id.id,
            }
        )

    def _create_posted_invoice(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "partner_id": self.partner_ar.id,
                "journal_id": self.preprinted_journal.id,
                "invoice_date": time.strftime("%Y-01-15"),
                "invoice_line_ids": [(0, 0, {"product_id": self.product_a.id, "quantity": 1, "price_unit": 100.0})],
            }
        )
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(invoice.invoice_filter_type_domain, "sale")
        return invoice

    def _installed_auth_fields(self, invoice):
        return [pair for pair in AFIP_AUTH_FIELDS if pair[0] in invoice._fields and pair[1] in invoice._fields]

    def test_cancel_invoice_not_authorized_by_afip(self):
        """Sin autorización de AFIP la factura se cancela, sin AttributeError."""
        invoice = self._create_posted_invoice()
        invoice.button_cancel()
        self.assertEqual(invoice.state, "cancel")

    def test_afip_authorized_is_false_without_authorization(self):
        """El helper no levanta aunque no exista ninguno de los dos pares de campos."""
        invoice = self._create_posted_invoice()
        self.assertFalse(invoice._l10n_ar_afip_authorized())

    def test_cancel_is_blocked_when_authorized_by_afip(self):
        """Con CAE la cancelación sigue bloqueada, sea cual sea el par de campos."""
        invoice = self._create_posted_invoice()
        available = self._installed_auth_fields(invoice)
        if not available:
            self.skipTest("Neither l10n_ar_edi nor l10n_ar_afipws_fe is installed")
        mode_field, code_field = available[0]
        invoice.write({mode_field: "CAE", code_field: "12345678901234"})
        self.assertTrue(invoice._l10n_ar_afip_authorized())
        with self.assertRaises(UserError):
            invoice.button_cancel()
        self.assertEqual(invoice.state, "posted")
