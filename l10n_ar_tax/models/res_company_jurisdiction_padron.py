import base64
import logging
import os
import re
import shutil
import subprocess
import tempfile
import zipfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

GREP_TIMEOUT = 30
# Magic bytes de un ZIP: archivo con contenido, vacio y multi-volumen.
ZIP_MAGIC_BYTES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


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
            if rec.state_id.jurisdiction_code not in ["901", "902", "921"]:
                raise ValidationError(_("The padron for %s is not implemented.") % rec.state_id.name)

    @api.constrains("state_id", "file_padron")
    def _check_santa_fe_file_padron_format(self):
        """Validar que para Santa Fe solo se permiten archivos ZIP comprimidos."""
        for rec in self:
            if not rec._is_santa_fe_jurisdiction() or not rec.file_padron:
                continue

            file_content = base64.b64decode(rec.file_padron)
            if not rec._has_zip_filename() or not rec._is_zip_content(file_content):
                raise ValidationError(_("Only compressed ZIP files are allowed for Santa Fe."))

    @api.constrains("state_id", "file_padron")
    def _check_agip_file_padron_format(self):
        """Validar que para AGIP (CABA) solo se permiten archivos comprimidos: RAR
        tal como lo publica AGIP, o ZIP si se re-comprime."""
        for rec in self:
            if not rec._is_agip_jurisdiction() or not rec.file_padron:
                continue

            file_content = base64.b64decode(rec.file_padron)
            if not rec._has_compressed_filename() or not rec._is_compressed_content(file_content):
                raise ValidationError(_("Only compressed ZIP or RAR files are allowed for AGIP (CABA)."))
            # Validamos acá y no al liquidar: si falta la lib de rar queremos que se
            # entere quien sube el archivo, no quien emite el comprobante.
            if rec._is_rar_content(file_content) and not rec._rar_support_available():
                raise ValidationError(
                    _(
                        "This database cannot read RAR files (the 'unrar' library is not installed). "
                        "Please upload the AGIP padron as a ZIP file instead."
                    )
                )

    @api.depends("company_id", "state_id")
    def name_get(self):
        res = []
        for padron in self:
            name = "%s: %s" % (padron.company_id.name, padron.state_id.name)
            res += [(padron.id, name)]
        return res

    def descompress_file(self, file_padron, dest_dir="/tmp"):
        """Extrae el padrón comprimido en dest_dir. Soporta ZIP (ARBA, Santa Fe) y
        RAR (AGIP publica el padrón de Regímenes Generales en .rar)."""
        file = base64.b64decode(file_padron)
        fobj = tempfile.NamedTemporaryFile(delete=False)
        fname = fobj.name
        fobj.write(file)
        fobj.close()
        os.makedirs(dest_dir, exist_ok=True)
        if self._is_rar_content(file):
            _logger.log(25, "Descompress rar file")
            # Import lazy: no declaramos unrar en external_dependencies para no
            # romper instalaciones que no usan el padrón de AGIP. Que la lib esté
            # disponible se valida al subir el archivo (_check_agip_file_padron_format).
            from unrar import rarfile

            rarfile.RarFile(fname).extractall(path=dest_dir)
        else:
            _logger.log(25, "Descompress zip file")
            with zipfile.ZipFile(fname, "r") as zip_file:
                zip_file.extractall(path=dest_dir)

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

    def _is_agip_jurisdiction(self):
        """Check if jurisdiction is CABA / AGIP (Regímenes Generales padron)"""
        self.ensure_one()
        return self.state_id and self.state_id.jurisdiction_code == "901"

    def _is_single_file_padron(self):
        """Jurisdicciones cuyo padrón viene en un único archivo con las dos alícuotas por
        CUIT y las mismas columnas, así que se leen igual (ver _read_padron_lines): Santa Fe
        (921, padrón PARP de API) y AGIP / CABA (901, Regímenes Generales). ARBA (902) no
        entra acá: publica percepciones y retenciones en archivos separados."""
        self.ensure_one()
        return self._is_santa_fe_jurisdiction() or self._is_agip_jurisdiction()

    def _is_zip_content(self, file_content):
        # Miramos los magic bytes en lugar de zipfile.is_zipfile(io.BytesIO(...)): el
        # BytesIO duplica en memoria todo el contenido, y el padron de AGIP pesa >100 MB.
        # Como efecto, alcanza con pasar los primeros bytes del archivo.
        return file_content[:4] in ZIP_MAGIC_BYTES

    def _is_rar_content(self, file_content):
        # Magic bytes de RAR: "Rar!\x1a\x07" (común a v4 y v5).
        return file_content.startswith(b"Rar!\x1a\x07")

    def _rar_support_available(self):
        """La lib unrar no está en external_dependencies (no queremos condicionar la
        instalación del módulo a un padrón puntual), así que chequeamos en runtime."""
        try:
            from unrar import rarfile  # noqa: F401

            return True
        except Exception:
            return False

    def _is_compressed_content(self, file_content):
        return self._is_zip_content(file_content) or self._is_rar_content(file_content)

    def _has_zip_filename(self):
        self.ensure_one()
        return bool(self.filename and self.filename.lower().endswith(".zip"))

    def _has_compressed_filename(self):
        self.ensure_one()
        return bool(self.filename and self.filename.lower().endswith((".zip", ".rar")))

    def _read_padron_lines(self, lines, cuit):
        """Layout del padrón de archivo único, compartido por Santa Fe (PARP) y AGIP:
        F.PUBLIC;F.VIGEN.DESDE;F.VIGEN.HASTA;NRO.CUIT   ;TIPO CONTRIB;MARCA ALTA;MARCA ALICUOTA;ALIC.PERCEP;ALICUOTA RETENC;GRUPO PER.;GRUPO RETEN;RAZON SOCIAL
        Returns: (is_in_padron, aliquot_ret, aliquot_per)
        """
        aliquot_ret = False
        aliquot_per = False
        is_in_padron = False
        for line in lines:
            if not line:
                continue
            # Algunos padrones (AGIP) traen bytes nulos y BOM en la primera columna.
            values = [value.replace("\0", "").strip() for value in line.split(";")]
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

    def _find_padron_aliquot(self, path, cuit):
        """Busca el CUIT en un padrón de archivo único (ver _is_single_file_padron) y
        devuelve (is_in_padron, aliquot_ret, aliquot_per).

        Filtra los candidatos con grep -F (en C) porque el padrón de AGIP tiene del
        orden de 1.5M de líneas; la comparación exacta por columna la hace
        _read_padron_lines para descartar falsos positivos (CUIT como substring de otro
        campo). Si grep timeoutea damos error en lugar de devolver una alícuota de castigo
        por no haber podido leer el padrón.
        """
        try:
            result = subprocess.run(
                # -a: los padrones pueden traer bytes nulos y grep los trataría como binarios
                ["grep", "-a", "-F", cuit, path],
                capture_output=True,
                encoding="latin-1",
                timeout=GREP_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            _logger.warning("Padrón: la búsqueda del cuit %s en %s superó el timeout.", cuit, path)
            raise UserError(
                _(
                    "The aliquot padron could not be read: looking up CUIT %s took too long. Please try "
                    "again in a few minutes or enter the tax rate manually on the contact."
                )
                % cuit
            )
        return self._read_padron_lines(result.stdout.splitlines(), cuit)

    def _find_padron_file(self, rootdir):
        fallback_match = False
        any_file_match = False
        for subdir, dirs, files in os.walk(rootdir):
            for filename in files:
                lower_filename = filename.lower()
                if lower_filename.endswith((".csv", ".txt")):
                    if "parp" in lower_filename:
                        return os.path.join(subdir, filename)
                    if not fallback_match:
                        fallback_match = os.path.join(subdir, filename)
                elif not any_file_match:
                    # El padrón de AGIP viene con nombre y extensión variables dentro del .rar
                    any_file_match = os.path.join(subdir, filename)
        return fallback_match or any_file_match

    def _get_padron_tmp_dir(self):
        # Dir por padron+periodo: no mezcla archivos de otro mes.
        self.ensure_one()
        return "/tmp/l10n_ar_padron_%s_%s_%s" % (
            self.id,
            self.l10n_ar_padron_from_date,
            self.l10n_ar_padron_to_date,
        )

    def _ensure_padron_file_extracted(self):
        """Descomprime el padrón una sola vez y lo deja en el directorio temporal del
        período: de ahí en más todas las búsquedas usan ese archivo, hasta que se reinicie
        el pod (igual que el padrón de Santa Fe).

        La descompresión va a un directorio staging que ninguna búsqueda mira y recién al
        terminar se publica moviéndolo con os.rename, que es atómico. Por eso ningún worker
        puede encontrar el archivo antes de que esté completamente descomprimido: o el
        directorio del período no existe, o tiene la extracción completa.
        """
        self.ensure_one()
        tmp_dir = self._get_padron_tmp_dir()
        path_file = self._find_padron_file(tmp_dir)
        if path_file:
            return path_file

        # Sniff de los primeros bytes: alcanza para saber si viene comprimido y evita
        # decodificar 100 MB de base64 (padron de AGIP) solo para chequear el formato.
        if self._is_compressed_content(base64.b64decode(self.file_padron[:8])):
            staging_dir = tempfile.mkdtemp(prefix="l10n_ar_padron.staging-", dir=os.path.dirname(tmp_dir))
            try:
                self.descompress_file(self.file_padron, dest_dir=staging_dir)
                # rename no reemplaza un directorio con contenido, y acá sabemos que lo que
                # haya en tmp_dir no sirve (no encontramos el padrón).
                shutil.rmtree(tmp_dir, ignore_errors=True)
                os.rename(staging_dir, tmp_dir)
            except Exception:
                shutil.rmtree(staging_dir, ignore_errors=True)
                raise
            path_file = self._find_padron_file(tmp_dir)
            if not path_file:
                raise ValidationError(_("The compressed file does not contain the padron in CSV or TXT format."))
            return path_file

        # CSV directo (no comprimido): lo persistimos para no re-decodificar cada vez.
        file_content = base64.b64decode(self.file_padron)
        os.makedirs(tmp_dir, exist_ok=True)
        path_file = os.path.join(tmp_dir, "padron.csv")
        with open(path_file, "w", encoding="latin-1") as fp:
            fp.write(file_content.decode("latin-1"))
        return path_file

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

        # Check if the whole padron comes in a single file (Santa Fe, AGIP)
        if self._is_single_file_padron():
            return self._find_padron_aliquot(self._ensure_padron_file_extracted(), partner.vat)
        else:
            # Original logic for other padron types (ARBA, etc)
            tmp_dir = self._get_padron_tmp_dir()
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
