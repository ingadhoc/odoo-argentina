from odoo.tests import Form, common, tagged


@tagged("post_install", "-at_install")
class TestResPartnerSanitize(common.TransactionCase):
    """Sanitización del VAT con caracteres ocultos (tarea #66709).

    El error sólo se dispara en Adhoc por el onchange ``_onchange_ar_identification_fields``
    de ``l10n_ar_ux`` (que llama a ``_get_id_number_sanitize``). Por eso la lógica
    vive acá: la sanitización usa regex en vez de ``stdnum.ar.cuit.compact``, que
    no limpia caracteres ocultos y hacía fallar el ``int()``.
    """

    # Word joiner (U+2060): el carácter oculto del traceback original.
    HIDDEN_CHAR = chr(0x2060)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Reutilizamos el partner CUIT que ya provee l10n_ar (data, siempre cargado).
        cls.partner = cls.env.ref("l10n_ar.partner_afip")
        cls.ar = cls.env.ref("base.ar")
        cls.it_dni = cls.env.ref("l10n_ar.it_dni")  # AFIP 96
        cls.it_passport = cls.env.ref("l10n_latam_base.it_pass")  # AFIP 94

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

    def test_onchange_formats_cuit_with_hidden_char(self):
        """El onchange limpia el VAT del CUIT dejando sólo el número y permite guardar."""
        cuit = self.partner.vat
        with Form(self.partner) as form:
            form.vat = self.HIDDEN_CHAR + cuit
        self.assertEqual(self.partner.vat, cuit)

    def test_onchange_formats_dni(self):
        """El DNI también es un documento numérico argentino: se formatea.

        No guardamos el Form: el onchange dispara al setear el VAT, y evitar el
        ``save`` desacopla el test de campos requeridos que agregan otros módulos
        (p. ej. ``sire_born_country_id`` de ``l10n_ar_txt_sire``).
        """
        form = Form(self.env["res.partner"])
        form.name = "Test DNI"
        form.country_id = self.ar
        form.l10n_latam_identification_type_id = self.it_dni
        form.vat = "30.717.808"
        self.assertEqual(form.vat, "30717808")

    def test_onchange_keeps_non_numeric_doc_untouched(self):
        """Un documento no numérico (pasaporte) puede tener letras: no se toca."""
        form = Form(self.env["res.partner"])
        form.name = "Test passport"
        form.country_id = self.ar
        form.l10n_latam_identification_type_id = self.it_passport
        form.vat = "AB123456"
        self.assertEqual(form.vat, "AB123456")
