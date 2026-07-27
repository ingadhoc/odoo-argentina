import base64
import io
import logging
import os
import re
import subprocess
import tempfile
import zipfile

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

GREP_TIMEOUT = 30


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

    def descompress_file(self, file_padron, dest_dir="/tmp"):
        _logger.log(25, "Descompress zip file")
        try:
            file = base64.b64decode(file_padron)
        except:
            file = base64.decodestring(file_padron)
        fobj = tempfile.NamedTemporaryFile(delete=False)
        fname = fobj.name
        fobj.write(file)
        fobj.close()
        f = open(fname, "r+b")
        f.write(base64.b64decode(file_padron))
        with zipfile.ZipFile(f, "r") as zip_file:
            zip_file.extractall(path=dest_dir)
            zip_file.close()

    def find_aliquot(self, path, cuit):
        """We try to find aliqut and number for a partner given"""
        # grep -F filtra candidatos en C; el split+comparación exacta abajo
        # descarta falsos positivos (CUIT como substring de otro campo).
        result = subprocess.run(
            ["grep", "-F", cuit, path],
            capture_output=True,
            text=True,
            timeout=GREP_TIMEOUT,
        )
        for line in result.stdout.splitlines():
            values = line.split(";")
            if len(values) > 8 and values[4] == cuit:
                return values[3], values[8]
        return False, False

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

    def _find_parp_file(self, rootdir):
        fallback_match = False
        for subdir, dirs, files in os.walk(rootdir):
            for filename in files:
                lower_filename = filename.lower()
                if lower_filename.endswith((".csv", ".txt")):
                    if "parp" in lower_filename:
                        return os.path.join(subdir, filename)
                    if not fallback_match:
                        fallback_match = os.path.join(subdir, filename)
        return fallback_match

    def _get_parp_tmp_dir(self):
        # Dir por padron+periodo: no mezcla archivos de otro mes.
        self.ensure_one()
        return "/tmp/l10n_ar_padron_%s_%s_%s" % (
            self.id,
            self.l10n_ar_padron_from_date,
            self.l10n_ar_padron_to_date,
        )

    def _ensure_parp_file_extracted(self):
        # Extrae/persiste una sola vez y reutiliza (antes se re-decodificaba/re-unzipeaba por CUIT).
        self.ensure_one()
        tmp_dir = self._get_parp_tmp_dir()
        path_file = self._find_parp_file(tmp_dir)
        if path_file:
            return path_file

        file_content = base64.b64decode(self.file_padron)
        if self._is_zip_content(file_content):
            self.descompress_file(self.file_padron, dest_dir=tmp_dir)
            path_file = self._find_parp_file(tmp_dir)
            if not path_file:
                raise ValidationError("El archivo ZIP no contiene un padrón PARP en formato CSV o TXT.")
            return path_file

        # CSV directo (no ZIP): lo persistimos para no re-decodificar cada vez.
        os.makedirs(tmp_dir, exist_ok=True)
        path_file = os.path.join(tmp_dir, "padron.csv")
        with open(path_file, "w", encoding="latin-1") as fp:
            fp.write(file_content.decode("latin-1"))
        return path_file

    def _read_parp_from_binary(self, cuit):
        """Read PARP (padrón Santa Fe) CSV directly from file_padron binary field
        or from ZIP if the binary is a ZIP file.
        PARP format: F.PUBLIC;F.VIGEN.DESDE;F.VIGEN.HASTA;NRO.CUIT   ;TIPO CONTRIB;MARCA ALTA;MARCA ALICUOTA;ALIC.PERCEP;ALICUOTA RETENC;GRUPO PER.;GRUPO RETEN;RAZON SOCIAL
        Returns: (aliquot_ret, aliquot_per)
        """
        path_file = self._ensure_parp_file_extracted()
        with open(path_file, encoding="latin-1") as fp:
            return self._read_parp_lines(fp.readlines(), cuit)

    def find_file(self, rootdir, type_code):
        res = False
        date = str(self.l10n_ar_padron_from_date.month) + str(self.l10n_ar_padron_from_date.year)
        pattern = r"%s.{1}|.TXT\Z" % type_code + date
        for subdir, dirs, files in os.walk(rootdir):
            for f in files:
                if re.search(pattern, f):
                    res = f
                    break
        return res

    def _get_aliquot(self, partner):
        nro = False
        aliquot_ret = 0.0
        aliquot_per = 0.0

        # Check if this is Santa Fe PARP format
        if self._is_santa_fe_jurisdiction():
            # Read PARP directly from binary field
            is_in_padron, aliquot_ret, aliquot_per = self._read_parp_from_binary(partner.vat)
            return is_in_padron, aliquot_ret, aliquot_per
        else:
            # Original logic for other padron types (ARBA, etc)
            tmp_dir = self._get_parp_tmp_dir()
            padron_types = ["Per", "Ret"]
            for padron_type in padron_types:
                path_file = self.find_file(tmp_dir, padron_type)
                if not path_file:
                    self.descompress_file(self.file_padron, dest_dir=tmp_dir)
                    path_file = self.find_file(tmp_dir, padron_type)
                if path_file:
                    nro, aliquot = self.find_aliquot(os.path.join(tmp_dir, path_file), partner.vat)
                    if padron_type == "Per":
                        aliquot_per = aliquot and aliquot.replace(",", ".")
                    else:
                        aliquot_ret = aliquot and aliquot.replace(",", ".")
        return nro, aliquot_ret, aliquot_per

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
