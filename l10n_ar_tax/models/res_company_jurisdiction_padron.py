import base64
import io
import logging
import zipfile

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResCompanyJurisdictionPadron(models.Model):
    _name = "res.company.jurisdiction.padron"
    _description = "res.company.jurisdiction.padron"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    state_id = fields.Many2one("res.country.state", string="Jurisdiction", domain="[('country_id.code', '=', 'AR')]")
    file_padron = fields.Binary(
        "File",
        required=True,
    )
    l10n_ar_padron_from_date = fields.Date(
        "From Date",
        required=True,
    )
    l10n_ar_padron_to_date = fields.Date(
        "To Date",
        required=True,
    )

    filename = fields.Char("File Name")

    @api.constrains("state_id")
    def check_state_id(self):
        for rec in self:
            if rec.state_id.jurisdiction_code not in ["902", "921"]:
                raise ValidationError("El padron para (%s) no está implementado." % rec.state_id.name)

    @api.constrains("state_id", "file_padron")
    def _check_santa_fe_file_padron_format(self):
        """Validar que para Santa Fe solo se permiten archivos ZIP comprimidos."""
        for rec in self:
            if not rec._is_santa_fe_jurisdiction() or not rec.file_padron:
                continue

            file_content = base64.b64decode(rec.file_padron)
            if not rec._has_zip_filename() or not rec._is_zip_content(file_content):
                raise ValidationError(_("Only compressed ZIP files are allowed for Santa Fe."))

    @api.depends("company_id", "state_id")
    def name_get(self):
        res = []
        for padron in self:
            name = "%s: %s" % (padron.company_id.name, padron.state_id.name)
            res += [(padron.id, name)]
        return res

    def _is_santa_fe_jurisdiction(self):
        """Check if jurisdiction is Santa Fe (PARP format)"""
        self.ensure_one()
        return self.state_id and self.state_id.jurisdiction_code == "921"

    def _is_zip_content(self, file_content):
        return zipfile.is_zipfile(io.BytesIO(file_content))

    def _has_zip_filename(self):
        self.ensure_one()
        return bool(self.filename and self.filename.lower().endswith(".zip"))

    def _read_parp_lines(self, lines, cuit):
        aliquot_ret = False
        aliquot_per = False
        is_in_padron = False
        for line in lines:
            if not line:
                continue
            values = [value.strip() for value in line.split(";")]
            if len(values) <= 8:
                continue
            # CUIT is at index 3, compare as strings
            if values[3] == cuit:
                # Percepción at index 7, Retención at index 8
                # Convert to float, handling comma as decimal separator
                aliquot_per = float(values[7].replace(",", "."))
                aliquot_ret = float(values[8].replace(",", "."))
                is_in_padron = True
                break
        return is_in_padron, aliquot_ret, aliquot_per

    def _find_parp_member(self, names):
        """Devuelve el nombre del archivo PARP (.csv/.txt) dentro del ZIP,
        priorizando el que contenga 'parp'; si no hay, el primer .csv/.txt.
        """
        fallback_match = False
        for name in names:
            lower_name = name.lower()
            if lower_name.endswith((".csv", ".txt")):
                if "parp" in lower_name:
                    return name
                if not fallback_match:
                    fallback_match = name
        return fallback_match

    def _read_parp_from_binary(self, cuit):
        """Read PARP (padrón Santa Fe) CSV directly from file_padron binary field
        or from ZIP if the binary is a ZIP file.
        PARP format: F.PUBLIC;F.VIGEN.DESDE;F.VIGEN.HASTA;NRO.CUIT   ;TIPO CONTRIB;MARCA ALTA;MARCA ALICUOTA;ALIC.PERCEP;ALICUOTA RETENC;GRUPO PER.;GRUPO RETEN;RAZON SOCIAL
        Returns: (is_in_padron, aliquot_ret, aliquot_per)
        """
        file_content = base64.b64decode(self.file_padron)
        # is a ZIP file: leemos el miembro en memoria, sin extraer a disco
        if self._is_zip_content(file_content):
            with zipfile.ZipFile(io.BytesIO(file_content)) as zip_file:
                member = self._find_parp_member(zip_file.namelist())
                if not member:
                    raise ValidationError(_("El archivo ZIP no contiene un padrón PARP en formato CSV o TXT."))
                with zip_file.open(member) as parp_file:
                    lines = io.TextIOWrapper(parp_file, encoding="latin-1").readlines()
            return self._read_parp_lines(lines, cuit)

        # is a CSV file directly
        csv_text = file_content.decode("latin-1")
        return self._read_parp_lines(csv_text.split("\n"), cuit)

    def _find_aliquot_in_lines(self, lines, cuit):
        """Busca el CUIT en las líneas del padrón ARBA (separador ';') y devuelve
        (nro_comprobante, alícuota) o (False, False) si no figura.
        Formato ARBA: CUIT en índice 4, nro en índice 3, alícuota en índice 8.
        """
        for line in lines:
            values = line.split(";")
            if len(values) > 8 and values[4] == cuit:
                return values[3], values[8]
        return False, False

    def _get_arba_aliquot_from_zip(self, cuit):
        """Obtiene (nro, aliquot_ret, aliquot_per) del padrón ARBA leyendo el ZIP
        ``file_padron`` en memoria.

        Antes se extraía el ZIP a ``/tmp`` y se buscaba el archivo por nombre. Como
        ``/tmp`` es compartido y persiste entre consultas, podía quedar el padrón
        de otro período y leerse la alícuota equivocada (p. ej. traer la del mes
        anterior). Leyendo el ZIP de este registro en memoria eso no puede pasar.
        """
        self.ensure_one()
        nro = False
        aliquot_ret = False
        aliquot_per = False
        file_content = base64.b64decode(self.file_padron)
        with zipfile.ZipFile(io.BytesIO(file_content)) as zip_file:
            names = zip_file.namelist()
            for padron_type in ("Per", "Ret"):
                member = next((name for name in names if padron_type.lower() in name.lower()), False)
                if not member:
                    continue
                with zip_file.open(member) as member_file:
                    lines = io.TextIOWrapper(member_file, encoding="latin-1").readlines()
                member_nro, aliquot = self._find_aliquot_in_lines(lines, cuit)
                if padron_type == "Per":
                    aliquot_per = aliquot and aliquot.replace(",", ".")
                else:
                    aliquot_ret = aliquot and aliquot.replace(",", ".")
                if member_nro:
                    nro = member_nro
        return nro, aliquot_ret, aliquot_per

    def _get_aliquot(self, partner):
        # Santa Fe usa formato PARP; el resto (ARBA) usa un ZIP con archivos Per/Ret.
        if self._is_santa_fe_jurisdiction():
            return self._read_parp_from_binary(partner.vat)
        return self._get_arba_aliquot_from_zip(partner.vat)

    @api.model
    def _cron_clean_old_padron_files(self):
        """Delete old padron files to reduce storage usage."""
        last_year_date = fields.Date.subtract(fields.Date.start_of(fields.Date.context_today(self), "month"), years=1)
        if old_padrons := self.search(
            [
                ("l10n_ar_padron_to_date", "<", last_year_date),
            ]
        ):
            _logger.info(
                "Padron cleanup: deleting %s old padrones older than %s",
                len(old_padrons),
                last_year_date,
            )
            old_padrons.unlink()
