from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestL10nArWithholdingArRi
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestPaymentWithholdingValidation(TestL10nArWithholdingArRi):
    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.caba_tax_perception = self.env.ref("account.%i_ri_tax_percepcion_iibb_caba_aplicada" % self.env.company.id)
        # Create caba perception tax with amounts 1% and 2%
        self.caba_tax_perception_with_amount_1 = self.caba_tax_perception.copy(
            default={"amount_type": "percent", "amount": 1}
        )
        self.caba_tax_perception_with_amount_2 = self.caba_tax_perception.copy(
            default={"amount_type": "percent", "amount": 2}
        )

    def _create_invoice_with_caba_perception(self):
        # Create commercial partner company with CABA state
        commercial_partner = self.env["res.partner"].create(
            {
                "name": "Commercial Partner CABA",
                "country_id": self.env.ref("base.ar").id,
                "state_id": self.env.ref("base.state_ar_c").id,  # CABA state
                "l10n_ar_afip_responsibility_type_id": self.env.ref("l10n_ar.res_IVARI").id,
                "vat": "20055361682",
                "is_company": True,
            }
        )

        # Create child contact
        child_partner = self.env["res.partner"].create(
            {
                "name": "Contact Person",
                "parent_id": commercial_partner.id,
                "is_company": False,
                "state_id": self.env.ref("base.state_ar_c").id,  # CABA state
            }
        )

        # Add perception tax to commercial partner's l10n_ar_partner_tax_ids
        self.env["l10n_ar.partner.tax"].create(
            {
                "tax_id": self.caba_tax_perception_with_amount_1.id,
                "partner_id": commercial_partner.id,
                "company_id": self.company_ri.id,  # Use same company as invoice
                "from_date": fields.Date.from_string("2025-11-01"),
                "to_date": fields.Date.from_string("2025-11-30"),
            }
        )
        self.env["l10n_ar.partner.tax"].create(
            {
                "tax_id": self.caba_tax_perception_with_amount_2.id,
                "partner_id": commercial_partner.id,
                "company_id": self.company_ri.id,  # Use same company as invoice
                "from_date": fields.Date.from_string("2025-12-01"),
                "to_date": fields.Date.from_string("2025-12-30"),
            }
        )
        # Create customer invoice with contact partner (child)
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": child_partner.id,  # Using child contact
                "company_id": self.company_ri.id,  # Use same company as fiscal position
                "invoice_date": fields.Date.from_string("2025-11-11"),
                "date": fields.Date.from_string("2025-11-11"),
            }
        )

        # Create fiscal position for CABA with perception tax
        fiscal_position_caba = self.env["account.fiscal.position"].create(
            {
                "name": "Percepciones CABA Test",
                "l10n_ar_afip_responsibility_type_ids": [(6, 0, [self.env.ref("l10n_ar.res_IVARI").id])],
                "auto_apply": True,
                "country_id": self.env.ref("base.ar").id,
                "state_ids": [(6, 0, [self.env.ref("base.state_ar_c").id])],
            }
        )

        self.env["account.fiscal.position.l10n_ar_tax"].create(
            {
                "fiscal_position_id": fiscal_position_caba.id,
                "default_tax_id": self.caba_tax_perception.id,
                "tax_type": "perception",
                "webservice": "agip",
            }
        )

        # Forzar cómputo de la posición fiscal
        invoice._compute_fiscal_position_id()
        # Agregamos una línea en la factura
        invoice.invoice_line_ids = [
            Command.create(
                {
                    "name": "Test Product",
                    "quantity": 1,
                    "price_unit": 1000.0,
                    "product_id": self.product_a.id,
                }
            )
        ]
        # Computamos los impuestos en la factura
        invoice.invoice_line_ids._compute_tax_ids()
        return invoice

    def test_credit_note_original_date_usage(self):
        """
        Test que valida que las líneas de NC usen el mismo impuesto de percepción
        que las lineas de la factura original. Más información acá:
        https://github.com/ingadhoc/odoo-argentina/commit/1963b523e2e75de146db13d3a481e973be4240b7#diff-3bf88e64e3d85a6ac36eeb771c581952aeced14289109b6209df2249bfe7e1e0R23
        """
        # Create original invoice date
        invoice = self._create_invoice_with_caba_perception()

        # Post the original invoice first
        invoice.action_post()

        nc_date = fields.Date.from_string("2025-12-02")
        refund_wizard = (
            self.env["account.move.reversal"]
            .with_context(**{"active_ids": [invoice.id], "active_model": "account.move"})
            .create({"reason": "Mercadería defectuosa", "journal_id": invoice.journal_id.id, "date": nc_date})
        )

        res = refund_wizard.refund_moves()
        refund = self.env["account.move"].browse(res["res_id"])
        refund._compute_fiscal_position_id()
        refund.invoice_line_ids._compute_tax_ids()
        self.assertEqual(invoice.invoice_line_ids.tax_ids, refund.invoice_line_ids.tax_ids)

    def test_customer_invoice_perception_from_commercial_partner(self):
        """
        Test que valida que valida que las percepciones en facturas de clientes
        se apliquen desde el commercial_partner_id.
        Ver https://github.com/ingadhoc/odoo-argentina/commit/1963b523e2e75de146db13d3a481e973be4240b7#diff-ea8ccac043f28a709a0d4ac12356fdc7b4cc46469017209e014568f9f9606495R15
        """
        invoice = self._create_invoice_with_caba_perception()
        # Nos aseguramos que la percepción venga del commercial_partner_id
        self.assertIn(
            invoice.partner_id.commercial_partner_id.l10n_ar_partner_perception_ids.filtered(
                lambda x: x.from_date <= invoice.date and invoice.date <= x.to_date
            ).tax_id,
            invoice.invoice_line_ids.tax_ids,
        )
        self.assertNotIn(invoice.partner_id.l10n_ar_partner_perception_ids.tax_id, invoice.invoice_line_ids.tax_ids)
