from odoo.tests import tagged
from odoo.tools import safe_eval

from .common import L10nArTaxPaymentCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestWithholdingCertificatesMail(L10nArTaxPaymentCommon):
    """Task 71431 / ticket 120699: sending a supplier payment by email must attach ONE PDF holding all its withholding
    certificates (one page per withholding) instead of one PDF -and one wkhtmltopdf run- per withholding.

    The per-withholding renders saturated the HTTP workers of a customer with payments carrying 5/6 withholdings,
    taking the instance down (error 500).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref("l10n_ar_tax.action_report_withholding_certificate")
        cls.receipt_template = cls.env.ref("account.mail_template_data_payment_receipt")

    def _posted_payment(self, document_number, price_unit=100000.0, taxes=None):
        """A posted supplier payment of a bill of price_unit + VAT, withholding IIBB 3% and earnings 6% by default."""
        taxes = taxes or (self.tax_iibb_untaxed | self.tax_earnings)
        return self._create_payment(self._create_bill(price_unit, document_number), taxes)

    def _new_composer(self, payments, composition_mode="comment"):
        return (
            self.env["mail.compose.message"]
            .with_context(active_model="account.payment", active_ids=payments.ids)
            .create(
                {
                    "model": "account.payment",
                    "res_ids": str(payments.ids),
                    "template_id": self.receipt_template.id,
                    "composition_mode": composition_mode,
                }
            )
        )

    def _certificate_attachments(self, attachments, payment):
        return attachments.filtered(lambda a: a.name == payment._l10n_ar_withholding_certificates_filename())

    def test_01_single_sending_attaches_one_pdf(self):
        """The composer preview attaches ONE certificates PDF per payment (not one per withholding), reuses it across
        recomputes and hands the same attachment over to the outgoing message."""
        payment = self._posted_payment("1-714311")
        self._assert_withholding(payment, self.tax_iibb_untaxed, 100000.0, 3000.0)
        self._assert_withholding(payment, self.tax_earnings, 100000.0, 5527.80)

        composer = self._new_composer(payment)
        certificates = self._certificate_attachments(composer.attachment_ids, payment)
        self.assertEqual(len(certificates), 1, "The preview must hold a single PDF with all the certificates")
        self.assertTrue(certificates.name.endswith(".pdf"))
        self.assertEqual(certificates.mimetype, "application/pdf")

        # the preview is recomputed every time the wizard is edited: it must reuse the rendered attachment
        composer._compute_attachment_ids()
        self.assertEqual(
            self.env["ir.attachment"].search_count(
                [
                    ("name", "=", payment._l10n_ar_withholding_certificates_filename()),
                    ("res_model", "=", "mail.compose.message"),
                    ("res_id", "=", composer.id),
                ]
            ),
            1,
            "Recomputing the preview must not render nor create a new attachment",
        )

        attachment_ids = composer._prepare_mail_values(payment.ids)[payment.id]["attachment_ids"]
        self.assertIn(certificates.id, attachment_ids, "Sending must reuse the attachment rendered for the preview")
        self.assertEqual(
            len(self._certificate_attachments(self.env["ir.attachment"].browse(attachment_ids), payment)),
            1,
            "The outgoing mail must carry a single certificates PDF",
        )

    def test_02_mass_sending_attaches_one_pdf_per_payment(self):
        """Mass sending (no preview) renders and attaches a single certificates PDF per payment."""
        payments = self._posted_payment("1-714312") | self._posted_payment(
            "1-714313", price_unit=50000.0, taxes=self.tax_iibb_untaxed
        )
        mail_values = self._new_composer(payments, composition_mode="mass_mail")._prepare_mail_values(payments.ids)
        for payment in payments:
            attachments = self.env["ir.attachment"].browse(
                [command[1] for command in mail_values[payment.id]["attachment_ids"] if isinstance(command, tuple)]
            )
            self.assertEqual(
                len(self._certificate_attachments(attachments, payment)),
                1,
                "Mass sending must attach a single certificates PDF to payment %s" % payment.name,
            )

    def test_03_zero_amount_withholdings_are_excluded(self):
        """An earnings withholding at $0 (under the non taxable amount) is kept on the payment, but it must not
        trigger any certificate attachment."""
        payment = self._posted_payment("1-714314", price_unit=5000.0, taxes=self.tax_earnings)
        self._assert_withholding(payment, self.tax_earnings, 5000.0, 0.0)
        self.assertFalse(
            self._certificate_attachments(self._new_composer(payment).attachment_ids, payment),
            "A payment whose withholdings are all at $0 must not attach any certificate",
        )

    def test_04_report_renders_one_document_per_withholding(self):
        """A single render call over all the withholdings produces one document per withholding (the template
        iterates over docs), which the PDF engine turns into one page each and merges into a single file."""
        withholdings = self._posted_payment("1-714315").withholding_line_ids
        self.assertEqual(len(withholdings), 2)
        html_content = self.env["ir.actions.report"]._render_qweb_html(self.report.report_name, withholdings.ids)[0]
        self.assertEqual(
            html_content.decode().count("CERTIFICADO DE RETENCIÓN"),
            len(withholdings),
            "The merged report must hold one certificate per withholding",
        )

    def test_05_cached_certificates_dropped_on_reset_to_draft(self):
        """The certificate PDF of each withholding is cached (attachment_use on the report): the attachment
        expression resolves on posted supplier payments and the cache is dropped when the payment is reset to draft."""
        payment = self._posted_payment("1-714316")
        withholdings = payment.withholding_line_ids
        self.assertTrue(self.report.attachment_use)
        # in test mode reports render as HTML, so the real caching path does not run: simulate the attachment the PDF
        # engine saves, named by the report 'attachment' expression (the one retrieve_attachment evaluates)
        for withholding in withholdings:
            filename = safe_eval.safe_eval(self.report.attachment, {"object": withholding})
            self.assertTrue(filename, "The attachment expression must resolve for posted supplier withholdings")
            self.env["ir.attachment"].create(
                {
                    "name": filename,
                    "raw": b"%PDF-fake",
                    "res_model": withholding._name,
                    "res_id": withholding.id,
                    "type": "binary",
                }
            )
            self.assertTrue(self.report.retrieve_attachment(withholding))

        payment.action_draft()
        for withholding in withholdings:
            self.assertFalse(
                self.report.retrieve_attachment(withholding),
                "The cached certificate of withholding %s must be dropped on reset to draft" % withholding.name,
            )
