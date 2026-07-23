import base64
import io
import logging
import os
import re
import subprocess
import zipfile

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

AWK_TIMEOUT = 30


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
        # Decode once and extract in-memory: the previous version decoded the
        # base64 twice and round-tripped through a temp file.
        file = base64.b64decode(file_padron)
        with zipfile.ZipFile(io.BytesIO(file), "r") as zip_file:
            zip_file.extractall(path=dest_dir)

    def _lookup_aliquot_awk(self, path, cuit, cuit_col, nro_col, aliq_col):
        # Columna exacta (no substring): evita falsos positivos tipo grep.
        program = '$%d==c {print $%d";"$%d; exit}' % (cuit_col, nro_col, aliq_col)
        out = subprocess.run(
            ["awk", "-F", ";", "-v", "c=" + cuit, program, path],
            capture_output=True,
            text=True,
            timeout=AWK_TIMEOUT,
        ).stdout.strip()
        if not out:
            return False, False
        nro, aliq = out.split(";", 1)
        return nro, aliq

    def find_aliquot(self, path, cuit):
        # ARBA: cuit col 5, nro col 4, alícuota col 9 (1-based).
        return self._lookup_aliquot_awk(path, cuit, cuit_col=5, nro_col=4, aliq_col=9)

    def _is_santa_fe_jurisdiction(self):
        """Check if jurisdiction is Santa Fe (PARP format)"""
        self.ensure_one()
        return self.state_id and self.state_id.jurisdiction_code == "921"

    def _is_zip_content(self, file_content):
        return zipfile.is_zipfile(io.BytesIO(file_content))

    def _has_zip_filename(self):
        self.ensure_one()
        return bool(self.filename and self.filename.lower().endswith(".zip"))

    def _lookup_parp_aliquot_awk(self, path, cuit):
        # PARP: cuit col 4, percepción col 8, retención col 9 (1-based); gsub recorta padding.
        program = '{f=$4; gsub(/^[ \\t]+|[ \\t]+$/,"",f); if (f==c) {print $4";"$8";"$9; exit}}'
        out = subprocess.run(
            ["awk", "-F", ";", "-v", "c=" + cuit, program, path],
            capture_output=True,
            text=True,
            timeout=AWK_TIMEOUT,
        ).stdout.strip()
        if not out:
            return False, False, False
        _nro, per, ret = (value.strip() for value in out.split(";"))
        return True, float(ret.replace(",", ".")), float(per.replace(",", "."))

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
        # Extrae una sola vez y reutiliza (antes se re-decodificaba/re-unzipeaba por CUIT).
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
        Returns: (is_in_padron, aliquot_ret, aliquot_per)
        """
        path_file = self._ensure_parp_file_extracted()
        return self._lookup_parp_aliquot_awk(path_file, cuit)

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
        self.ensure_one()
        return self._get_aliquot_cached(partner.vat)

    @tools.ormcache("self.id", "self.write_date", "cuit")
    def _get_aliquot_cached(self, cuit):
        # Caché por-CUIT; write_date invalida sola al recargar el padrón.
        if self._is_santa_fe_jurisdiction():
            # Read PARP directly from binary field
            return self._read_parp_from_binary(cuit)

        # Original logic for other padron types (ARBA, etc)
        tmp_dir = self._get_parp_tmp_dir()
        nro = False
        aliquot_ret = 0.0
        aliquot_per = 0.0
        for padron_type in ("Per", "Ret"):
            path_file = self.find_file(tmp_dir, padron_type)
            if not path_file:
                self.descompress_file(self.file_padron, dest_dir=tmp_dir)
                path_file = self.find_file(tmp_dir, padron_type)
            if path_file:
                nro, aliquot = self.find_aliquot(os.path.join(tmp_dir, path_file), cuit)
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
