from dateutil.relativedelta import relativedelta
from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import Form, tagged


@tagged("-at_install", "post_install")
class TestCreditNotePerceptionRules(TestArWithholdingArRi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("l10n_ar_tax.credit_note_perception_rules", "True")
        # First day of a month, so each refund falls in a known monthly period after the invoice
        cls.invoice_date = fields.Date.today().replace(day=1) - relativedelta(months=6)
        company_id = cls.env.company.id
        cls.perc_caba = cls.env.ref("account.%i_ri_tax_percepcion_iibb_caba_aplicada" % company_id).copy(
            {"amount_type": "percent", "amount": 1, "l10n_ar_state_id": cls.env.ref("base.state_ar_c").id}
        )
        cls.perc_arba = cls.env.ref("account.%i_ri_tax_percepcion_iibb_ba_aplicada" % company_id).copy(
            {"amount_type": "percent", "amount": 1, "l10n_ar_state_id": cls.env.ref("base.state_ar_b").id}
        )
        cls.perc_cordoba = cls.env.ref("account.%i_ri_tax_percepcion_iibb_co_aplicada" % company_id).copy(
            {"amount_type": "percent", "amount": 1, "l10n_ar_state_id": cls.env.ref("base.state_ar_x").id}
        )
        cls.perceptions = cls.perc_caba | cls.perc_arba
        cls.fiscal_position = cls.env["account.fiscal.position"].create(
            {
                "name": "Percepciones CABA + ARBA + Córdoba",
                "l10n_ar_tax_ids": [
                    Command.create({"default_tax_id": tax.id, "tax_type": "perception"})
                    for tax in cls.perceptions | cls.perc_cordoba
                ],
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente CABA",
                "country_id": cls.env.ref("base.ar").id,
                "state_id": cls.env.ref("base.state_ar_c").id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_cuit").id,
                "vat": "20055361682",
                "is_company": True,
            }
        )
        for tax in cls.perceptions | cls.perc_cordoba:
            cls.env["l10n_ar.partner.tax"].create(
                {"tax_id": tax.id, "partner_id": cls.partner.id, "company_id": company_id}
            )
        cls.invoice = cls._create_document("out_invoice", cls.invoice_date)
        cls.invoice.action_post()

    @classmethod
    def _create_document(cls, move_type, date, taxes=None):
        return cls.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": cls.partner.id,
                "fiscal_position_id": cls.fiscal_position.id,
                "invoice_date": date,
                "date": date,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_a.id,
                            "price_unit": 1000.0,
                            "tax_ids": [Command.set((cls.tax_21 | (cls.perceptions if taxes is None else taxes)).ids)],
                        }
                    )
                ],
            }
        )

    def _reverse_invoice(self, months_after, price_unit=None, invoice=None):
        """Reverse the invoice and, for a partial refund, edit the price as the form would."""
        invoice = invoice or self.invoice
        refund_date = self.invoice_date + relativedelta(months=months_after)
        wizard = (
            self.env["account.move.reversal"]
            .with_context(active_ids=invoice.ids, active_model="account.move")
            .create({"reason": "Devolución", "journal_id": invoice.journal_id.id, "date": refund_date})
        )
        refund = self.env["account.move"].browse(wizard.refund_moves()["res_id"])
        if price_unit:
            line = refund.invoice_line_ids
            refund.write({"invoice_line_ids": [Command.update(line.id, {"price_unit": price_unit})]})
        return refund

    def _manual_refund(self, months_after):
        return self._create_document("out_refund", self.invoice_date + relativedelta(months=months_after))

    def _reverse_invoice_without_arba(self):
        """Reverse an invoice whose ARBA perception was removed by hand."""
        invoice = self._create_document("out_invoice", self.invoice_date, taxes=self.perc_caba)
        invoice.action_post()
        return self._reverse_invoice(1, invoice=invoice)

    def test_credit_note_perceptions_by_jurisdiction(self):
        """AGIP and ARBA perceptions only stay on credit notes that fully refund an invoice, as the invoice had them;
        AGIP only up to the 2 monthly periods after it. VAT is never touched and the tax lines follow the line taxes.
        """
        cases = [
            (
                "NC total en el segundo período siguiente: AGIP y ARBA",
                lambda: self._reverse_invoice(2),
                self.perceptions,
            ),
            ("NC total en el tercer período siguiente: solo ARBA", lambda: self._reverse_invoice(3), self.perc_arba),
            (
                "NC parcial: sin percepciones",
                lambda: self._reverse_invoice(1, price_unit=500.0),
                self.perc_caba.browse(),
            ),
            (
                "NC total de una factura sin ARBA: no la agrega",
                self._reverse_invoice_without_arba,
                self.perc_caba,
            ),
            (
                "NC manual sin factura que anule: sin percepciones",
                lambda: self._manual_refund(1),
                self.perc_caba.browse(),
            ),
        ]
        for label, create_refund, expected in cases:
            with self.subTest(label):
                refund = create_refund()
                self.assertEqual(refund.invoice_line_ids.tax_ids & self.perceptions, expected)
                self.assertIn(self.tax_21, refund.invoice_line_ids.tax_ids)
                self.assertEqual(refund.line_ids.tax_line_id & self.perceptions, expected)

        with self.subTest("NC total de una factura con percepciones en una sola línea: las respeta por línea"):
            invoice = self._create_document("out_invoice", self.invoice_date)
            invoice.invoice_line_ids = [
                Command.create(
                    {"product_id": self.product_b.id, "price_unit": 500.0, "tax_ids": [Command.set(self.tax_21.ids)]}
                )
            ]
            invoice.action_post()
            refund = self._reverse_invoice(1, invoice=invoice)
            for product, expected in ((self.product_a, self.perceptions), (self.product_b, self.perc_caba.browse())):
                line = refund.invoice_line_ids.filtered(lambda x, product=product: x.product_id == product)
                self.assertEqual(line.tax_ids & self.perceptions, expected)
            self.assertEqual(refund.line_ids.tax_line_id & self.perceptions, self.perceptions)
            # 1% over the 1000 of the product A line only
            caba_amount = sum(refund.line_ids.filtered(lambda x: x.tax_line_id == self.perc_caba).mapped("balance"))
            self.assertAlmostEqual(abs(caba_amount), 10.0)

        with self.subTest("Las percepciones de otras jurisdicciones (Córdoba) quedan igual que sin el parámetro"):
            taxes = self.perceptions | self.perc_cordoba
            invoice = self._create_document("out_invoice", self.invoice_date, taxes=taxes)
            invoice.action_post()
            refunds = {
                "total": lambda: self._reverse_invoice(1, invoice=invoice),
                "parcial": lambda: self._reverse_invoice(1, price_unit=500.0, invoice=invoice),
                "manual": lambda: self._create_document("out_refund", self.invoice_date, taxes=taxes),
            }
            for kind, create_refund in refunds.items():
                cordoba = {}
                for flag in ("False", "True"):
                    self.env["ir.config_parameter"].sudo().set_param("l10n_ar_tax.credit_note_perception_rules", flag)
                    cordoba[flag] = create_refund().invoice_line_ids.tax_ids & self.perc_cordoba
                self.assertEqual(cordoba["True"], cordoba["False"], kind)
            self.assertTrue(cordoba["True"], "the manual credit note keeps the Córdoba perception")

        with self.subTest("Desde el formulario, pasar la fecha al tercer período siguiente quita AGIP"):
            refund = self._reverse_invoice(1)
            with Form(refund) as refund_form:
                refund_form.invoice_date = self.invoice_date + relativedelta(months=3)
                # Before saving: the onchange already applied the rules
                with refund_form.invoice_line_ids.edit(0) as line_form:
                    self.assertNotIn(self.perc_caba, line_form.tax_ids)
                    self.assertIn(self.perc_arba, line_form.tax_ids)
            self.assertEqual(refund.invoice_line_ids.tax_ids & self.perceptions, self.perc_arba)
            self.assertEqual(refund.line_ids.tax_line_id & self.perceptions, self.perc_arba)

        with self.subTest("Sin el parámetro, la NC manual conserva las percepciones"):
            self.env["ir.config_parameter"].sudo().set_param("l10n_ar_tax.credit_note_perception_rules", "False")
            refund = self._manual_refund(1)
            self.assertEqual(refund.invoice_line_ids.tax_ids & self.perceptions, self.perceptions)
            self.assertEqual(refund.line_ids.tax_line_id & self.perceptions, self.perceptions)
