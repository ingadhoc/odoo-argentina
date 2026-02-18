import base64
import logging
import os
import re
import tempfile
import zipfile

from odoo import api, fields, models
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

    @api.depends("company_id", "state_id")
    def name_get(self):
        res = []
        for padron in self:
            name = "%s: %s" % (padron.company_id.name, padron.state_id.name)
            res += [(padron.id, name)]
        return res

    def descompress_file(self, file_padron):
        _logger.log(25, "Descompress zip file")
        ruta_extraccion = "/tmp"
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
            zip_file.extractall(path=ruta_extraccion)
            zip_file.close()

    def find_aliquot(self, path, cuit):
        """We try to find aliqut and number for a partner given"""
        with open(path) as fp:
            aliq = False
            nro = False
            for line in fp.readlines():
                values = line.split(";")
                if values[4] == cuit:
                    aliq = values[8]
                    nro = values[3]
                    break
            return nro, aliq

    def _is_santa_fe_jurisdiction(self):
        """Check if jurisdiction is Santa Fe (PARP format)"""
        self.ensure_one()
        return self.state_id and self.state_id.jurisdiction_code == "921"

    def _read_parp_from_binary(self, cuit):
        """Read PARP (padrón Santa Fe) CSV directly from file_padron binary field
        PARP format: F.PUBLIC;F.VIGEN.DESDE;F.VIGEN.HASTA;NRO.CUIT   ;TIPO CONTRIB;MARCA ALTA;MARCA ALICUOTA;ALIC.PERCEP;ALICUOTA RETENC;GRUPO PER.;GRUPO RETEN;RAZON SOCIAL
        Returns: (aliquot_ret, aliquot_per)
        """
        aliquot_ret = False
        aliquot_per = False
        is_in_padron = False
        # Decode binary field to bytes
        file_content = base64.b64decode(self.file_padron)
        # Convert bytes to string
        csv_text = file_content.decode("latin-1")
        # Split by lines and process
        for line in csv_text.split("\n"):
            if not line:
                continue
            values = line.split(";")
            # CUIT is at index 3, compare as strings
            if values[3] == cuit:
                # Percepción at index 7, Retención at index 8
                # Convert to float, handling comma as decimal separator
                aliquot_per = float(values[7].replace(",", "."))
                aliquot_ret = float(values[8].replace(",", "."))
                is_in_padron = True
                break
        return is_in_padron, aliquot_ret, aliquot_per

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
            padron_types = ["Per", "Ret"]
            for padron_type in padron_types:
                path_file = self.find_file("/tmp/", padron_type)
                if not path_file:
                    self.descompress_file(self.file_padron)
                    path_file = self.find_file("/tmp/", padron_type)
                if path_file:
                    nro, aliquot = self.find_aliquot("/tmp/" + path_file, partner.vat)
                    if padron_type == "Per":
                        aliquot_per = aliquot and aliquot.replace(",", ".")
                    else:
                        aliquot_ret = aliquot and aliquot.replace(",", ".")
        return nro, aliquot_ret, aliquot_per
