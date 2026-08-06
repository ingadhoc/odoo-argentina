from odoo import Command, fields
from odoo.addons.l10n_ar_withholding.tests.test_withholding_ar_ri import TestArWithholdingArRi
from odoo.tests import tagged
from odoo.tools import safe_eval


@tagged("post_install_l10n", "post_install", "-at_install")
class TestWithholdingCertificatesMail(TestArWithholdingArRi):
    """Task 71431 / ticket 120699: sending a supplier payment by email must
    attach ONE PDF holding all its withholding certificates (one page per
    withholding) instead of one PDF -and one wkhtmltopdf run- per withholding.

    The per-withholding renders saturated the HTTP workers of a customer with
    payments carrying 5/6 withholdings, taking the instance down (error 500).
    """

    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.company_bank_journal = self.env["account.journal"].search(
            [("company_id", "=", self.company_ri.id), ("type", "=", "bank")], limit=1
        )
        self.report = self.env.ref("l10n_ar_tax.action_report_withholding_certificate")
        self.receipt_template = self.env.ref("account.mail_template_data_payment_receipt")

    def _create_posted_payment_with_withholdings(self, document_number, withholding_vals):
        """Supplier payment over a posted vendor bill, with the given manual
        withholding lines, posted (so the certificates get their number)."""
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.res_partner_adhoc.id,
                "move_type": "in_invoice",
                "company_id": self.company_ri.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 100000,
                            "tax_ids": [Command.set(self.tax_21.ids)],
                        }
                    ),
                ],
                "invoice_date": self.today,
                "l10n_latam_document_number": document_number,
            }
        )
        invoice.action_post()

        action_context = invoice.action_register_payment()["context"]
        payment = (
            self.env["account.payment"]
            .with_context(**action_context)
            .create(
                {
                    "journal_id": self.company_bank_journal.id,
                    "amount": invoice.amount_total,
                    "date": self.today,
                }
            )
        )
        payment.l10n_ar_withholding_line_ids = [Command.create(vals) for vals in withholding_vals]
        payment.action_post()
        return payment

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
        """The composer preview attaches ONE certificates PDF per payment (not
        one per withholding), reuses it across recomputes and hands the same
        attachment over to the outgoing message."""
        payment = self._create_posted_payment_with_withholdings(
            "1-714311",
            [
                {"tax_id": self.tax_wth_test_1.id, "base_amount": 100000.0, "amount": 3000.0},
                {"tax_id": self.tax_wth_test_2.id, "base_amount": 121000.0, "amount": 2500.0},
            ],
        )
        self.assertEqual(len(payment.l10n_ar_withholding_line_ids), 2)

        composer = self._new_composer(payment)
        certificates = self._certificate_attachments(composer.attachment_ids, payment)
        self.assertEqual(
            len(certificates), 1, "The preview must hold a single PDF with all the withholding certificates"
        )
        self.assertTrue(certificates.name.endswith(".pdf"))
        self.assertEqual(certificates.mimetype, "application/pdf")

        # Recomputing the preview (it runs every time the wizard is edited)
        # must reuse the rendered attachment instead of creating another one.
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

        mail_values = composer._prepare_mail_values(payment.ids)
        attachment_ids = mail_values[payment.id]["attachment_ids"]
        self.assertIn(certificates.id, attachment_ids, "Sending must reuse the attachment rendered for the preview")
        certificate_ids = [
            attachment_id
            for attachment_id in attachment_ids
            if attachment_id
            in self._certificate_attachments(self.env["ir.attachment"].browse(attachment_ids), payment).ids
        ]
        self.assertEqual(len(certificate_ids), 1, "The outgoing mail must carry a single certificates PDF")

    def test_02_mass_sending_attaches_one_pdf_per_payment(self):
        """Mass sending (no preview) renders and attaches a single certificates
        PDF per payment."""
        payment_1 = self._create_posted_payment_with_withholdings(
            "1-714312",
            [
                {"tax_id": self.tax_wth_test_1.id, "base_amount": 100000.0, "amount": 3000.0},
                {"tax_id": self.tax_wth_test_2.id, "base_amount": 121000.0, "amount": 2500.0},
            ],
        )
        payment_2 = self._create_posted_payment_with_withholdings(
            "1-714313",
            [{"tax_id": self.tax_wth_test_1.id, "base_amount": 50000.0, "amount": 1500.0}],
        )
        payments = payment_1 + payment_2

        composer = self._new_composer(payments, composition_mode="mass_mail")
        mail_values = composer._prepare_mail_values(payments.ids)
        for payment in payments:
            attachment_commands = [
                command for command in mail_values[payment.id]["attachment_ids"] if isinstance(command, tuple)
            ]
            attachments = self.env["ir.attachment"].browse([command[1] for command in attachment_commands])
            certificates = self._certificate_attachments(attachments, payment)
            self.assertEqual(
                len(certificates),
                1,
                "Mass sending must attach a single certificates PDF to payment %s" % payment.name,
            )

    def test_03_zero_amount_withholdings_are_excluded(self):
        """Withholdings at $0 (profits under the threshold) must not trigger
        any certificate attachment."""
        payment = self._create_posted_payment_with_withholdings(
            "1-714314",
            [{"tax_id": self.tax_wth_test_1.id, "base_amount": 100000.0, "amount": 0.0}],
        )
        composer = self._new_composer(payment)
        self.assertFalse(
            self._certificate_attachments(composer.attachment_ids, payment),
            "A payment whose withholdings are all at $0 must not attach any certificate",
        )

    def test_04_report_renders_one_document_per_withholding(self):
        """A single render call over all the withholdings produces one document
        per withholding (the template iterates over docs), which the PDF engine
        turns into one page each and merges into a single file."""
        payment = self._create_posted_payment_with_withholdings(
            "1-714315",
            [
                {"tax_id": self.tax_wth_test_1.id, "base_amount": 100000.0, "amount": 3000.0},
                {"tax_id": self.tax_wth_test_2.id, "base_amount": 121000.0, "amount": 2500.0},
            ],
        )
        withholdings = payment.l10n_ar_withholding_line_ids

        html_content, _content_type = self.env["ir.actions.report"]._render_qweb_html(
            self.report.report_name, withholdings.ids
        )
        self.assertEqual(
            html_content.decode().count("CERTIFICADO DE RETENCIÓN"),
            len(withholdings),
            "The merged report must hold one certificate per withholding",
        )

    def test_05_cached_certificates_dropped_on_reset_to_draft(self):
        """The certificate PDF of each withholding is cached (attachment_use on
        the report): the attachment expression resolves on posted supplier
        payments and the cache is dropped when the payment is reset to draft."""
        payment = self._create_posted_payment_with_withholdings(
            "1-714316",
            [
                {"tax_id": self.tax_wth_test_1.id, "base_amount": 100000.0, "amount": 3000.0},
                {"tax_id": self.tax_wth_test_2.id, "base_amount": 121000.0, "amount": 2500.0},
            ],
        )
        withholdings = payment.l10n_ar_withholding_line_ids

        self.assertTrue(self.report.attachment_use)
        # Simulate the cache the PDF engine saves on render (in test mode
        # reports render as HTML, so the real caching path does not run):
        # an attachment named as the report 'attachment' expression, linked to
        # each withholding. retrieve_attachment evaluates that same expression.
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
            self.assertTrue(
                self.report.retrieve_attachment(withholding),
                "retrieve_attachment must find the cached certificate of %s" % withholding.name,
            )

        # Resetting to draft invalidates the cache (the payment may be edited
        # and reposted under the same name).
        payment.action_draft()
        for withholding in withholdings:
            self.assertFalse(
                self.report.retrieve_attachment(withholding),
                "The cached certificate of withholding %s must be dropped on reset to draft" % withholding.name,
            )
