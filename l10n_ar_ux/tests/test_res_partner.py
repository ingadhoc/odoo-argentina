from odoo.tests import Form, common, tagged


@tagged("post_install", "-at_install")
class TestResPartnerSanitize(common.TransactionCase):
    """Sanitización del VAT (tarea #66709) — override de ``_get_id_number_sanitize``.

    El override hace dos cosas:

    1. Usa una regex en vez de ``stdnum.ar.cuit.compact``, que no limpia
       caracteres ocultos (p. ej. pegados desde Excel) y hacía fallar el
       ``int()`` del base ``l10n_ar`` al guardar un CUIL (AFIP 86, que pasa por
       ``_run_check_identification``).
    2. Sólo sanitiza documentos numéricos argentinos (CUIT/CUIL/DNI); los demás
       (pasaporte, SIGD, extranjeros) se preservan tal cual. Workaround del bug
       del base https://github.com/odoo/odoo/issues/272173.
    """

    # Word joiner (U+2060): el carácter oculto del traceback original.
    HIDDEN_CHAR = chr(0x2060)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Reutilizamos el partner CUIT que ya provee l10n_ar (data, siempre cargado).
        cls.partner = cls.env.ref("l10n_ar.partner_afip")
        cls.ar = cls.env.ref("base.ar")
        cls.it_passport = cls.env.ref("l10n_latam_base.it_pass")  # AFIP 94, puede tener letras

    def test_sanitize_cuit_with_hidden_char_no_traceback(self):
        """Un CUIT con carácter oculto no debe romper, debe devolver sólo dígitos."""
        cuit = self.partner.vat
        partner = self.partner.new({"vat": self.HIDDEN_CHAR + cuit}, origin=self.partner)
        self.assertEqual(partner._get_id_number_sanitize(), int(cuit))

    def test_sanitize_cuit_with_separators(self):
        """El CUIT con guiones se compacta a sólo dígitos."""
        cuit = self.partner.vat
        formatted = "%s-%s-%s" % (cuit[:2], cuit[2:10], cuit[10:])
        partner = self.partner.new({"vat": formatted}, origin=self.partner)
        self.assertEqual(partner._get_id_number_sanitize(), int(cuit))

    def test_sanitize_no_vat_returns_zero(self):
        partner = self.partner.new({"vat": False}, origin=self.partner)
        self.assertEqual(partner._get_id_number_sanitize(), 0)

    def test_sanitize_skips_non_numeric_doc(self):
        """Un documento no numérico (pasaporte) no se sanitiza: devuelve 0."""
        partner = self.partner.new(
            {"vat": "AAG756766", "l10n_latam_identification_type_id": self.it_passport.id},
            origin=self.partner,
        )
        self.assertEqual(partner._get_id_number_sanitize(), 0)

    def test_passport_letters_preserved_onchange(self):
        """Un pasaporte argentino con letras (AAG756766) se preserva al editar.

        Regresión del base v19: ``_run_check_identification`` le borraba las
        letras. Nuestro override devuelve 0 para no-numéricos, así el caller del
        base no reescribe el VAT.
        """
        form = Form(self.env["res.partner"])
        form.name = "Test passport"
        form.country_id = self.ar
        form.l10n_latam_identification_type_id = self.it_passport
        form.vat = "AAG756766"
        self.assertEqual(form.vat, "AAG756766")
