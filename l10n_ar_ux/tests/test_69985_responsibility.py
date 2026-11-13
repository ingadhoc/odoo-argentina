from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestMissingResponsibility(TestArCommon):
    """Sin la responsabilidad ARCA del contacto no podemos saber qué letras corresponden. Antes de este fix el
    dominio dejaba pasar los documentos sin letra (exterior y excepcionales) y se autoseleccionaba el primero,
    un Despacho de importación."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "Proveedor sin responsabilidad ARCA",
                "is_company": True,
                "country_id": cls.env.ref("base.ar").id,
                "l10n_ar_afip_responsibility_type_id": False,
            }
        )
        cls.purchase_journal = cls.env["account.journal"].search(
            [
                ("type", "=", "purchase"),
                ("company_id", "=", cls.env.company.id),
                ("l10n_latam_use_documents", "=", True),
            ],
            limit=1,
        )
        cls.responsible = cls.env.ref("l10n_ar.res_IVARI")

    def _new_bill(self):
        """Con create() y no con Form() a propósito: asignar el contacto en un Form dispara el warning de
        _onchange_afip_responsibility de l10n_ar y ensucia el log del build."""
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "journal_id": self.purchase_journal.id,
                "invoice_date": "2026-01-01",
            }
        )

    def test_no_document_proposed_without_responsibility(self):
        bill = self._new_bill()
        self.assertFalse(bill.l10n_latam_available_document_type_ids)
        self.assertFalse(bill.l10n_latam_document_type_id)

    def test_documents_are_proposed_again_once_the_partner_is_fixed(self):
        """Se completó la responsabilidad en el contacto (desde su ficha, un import, donde sea): al releer, la
        factura vuelve a proponer documentos."""
        bill = self._new_bill()
        self.assertFalse(bill.l10n_latam_available_document_type_ids)
        self.vendor.l10n_ar_afip_responsibility_type_id = self.responsible
        # El formulario recarga al volver a la factura; acá lo simulamos vaciando la caché.
        bill.invalidate_recordset()
        self.assertTrue(bill.l10n_latam_available_document_type_ids)

    def test_the_wizard_fixes_the_contact_and_refreshes_the_bill(self):
        """El aviso abre un wizard: al aceptar, la responsabilidad queda en el contacto y la factura vuelve a
        proponer documentos con el tipo ya elegido, sin recargar a mano."""
        bill = self._new_bill()
        action = bill.action_l10n_ar_ux_set_partner_responsibility()
        self.assertEqual(action["res_model"], "l10n_ar_ux.partner.responsibility")
        self.assertEqual(action["context"]["default_move_id"], bill.id)

        wizard = (
            self.env[action["res_model"]]
            .with_context(**action["context"])
            .create({"responsibility_id": self.responsible.id})
        )
        self.assertEqual(wizard.partner_id, self.vendor)
        wizard.action_apply()

        self.assertEqual(self.vendor.l10n_ar_afip_responsibility_type_id, self.responsible)
        self.assertTrue(bill.l10n_latam_available_document_type_ids)
        self.assertEqual(bill.l10n_latam_document_type_id.l10n_ar_letter, "A")

    def test_draft_without_responsibility_can_be_saved_from_the_form(self):
        """The button is type="object", so the web client saves the draft before running it. With no document
        type to pick, a required field in the view would block that save and the wizard would never open."""
        sale_journal = self.env["account.journal"].search(
            [
                ("type", "=", "sale"),
                ("company_id", "=", self.env.company.id),
                ("l10n_latam_use_documents", "=", True),
            ],
            limit=1,
        )
        for move_type, journal in [("out_invoice", sale_journal), ("in_invoice", self.purchase_journal)]:
            with self.subTest(move_type=move_type):
                with self.assertLogs("odoo.tests.form.onchange", level="WARNING"):
                    move_form = Form(
                        self.env["account.move"].with_context(
                            default_move_type=move_type, default_journal_id=journal.id
                        )
                    )
                    move_form.partner_id = self.vendor
                    move_form.invoice_date = "2026-01-01"
                move = move_form.save()
                self.assertFalse(move.l10n_latam_document_type_id)
                action = move.action_l10n_ar_ux_set_partner_responsibility()
                self.assertEqual(action["context"]["default_move_id"], move.id)

    def test_partner_with_responsibility_is_not_affected(self):
        self.vendor.l10n_ar_afip_responsibility_type_id = self.responsible
        bill = self._new_bill()
        self.assertTrue(bill.l10n_latam_available_document_type_ids)
        self.assertEqual(bill.l10n_latam_document_type_id.l10n_ar_letter, "A")
