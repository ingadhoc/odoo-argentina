from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from io import BytesIO
import zipfile
import tempfile
import os
import re
import logging
import base64
_logger = logging.getLogger(__name__)


class ResCompanyJurisdictionPadron(models.Model):
    _name = "res.company.jurisdiction.padron"
    _description = "res.company.jurisdiction.padron"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    jurisdiction_id = fields.Many2one(
        "account.account.tag",
        domain="[('applicability', '=', 'taxes'),('jurisdiction_code', '!=', False)]",
        required=True,
    )

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

    @api.constrains('jurisdiction_id')
    def check_jurisdiction_id(self):
        arba_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_902')
        santa_fe_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_921')
        for rec in self:
            if rec.jurisdiction_id not in [arba_tag, santa_fe_tag]:
                raise ValidationError("El padron para (%s) no está implementado." % rec.jurisdiction_id.name)

    @api.depends('company_id', 'jurisdiction_id')
    def name_get(self):
        res = []
        for padron in self:
            name = "%s: %s" % (padron.company_id.name,
                               padron.jurisdiction_id.name)
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
        f = open(fname, 'r+b')
        data = f.read()
        f.write(base64.b64decode(file_padron))
        with zipfile.ZipFile(f, 'r') as zip_file:
            zip_file.extractall(path=ruta_extraccion)
            zip_file.close()

    def find_aliquot(self, path, cuit):
        """We try to find aliqut and number for a partner given
        """
        with open(path, "r") as fp:
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
        santa_fe_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_921')
        return self.jurisdiction_id == santa_fe_tag

    def _read_parp_from_binary(self, cuit):
        """Read PARP CSV directly from file_padron binary field
        PARP format: fecha;fecha_desde;fecha_hasta;cuit;tipo;inscripto_convenio;inscripto_iibb;aliquota_retencion;aliquota_percepcion;
        Alícuotas "Castigo" o por Defecto: Si un sujeto pasible no figura en el padrón y no acredita su inscripción o exención: se aplica el 5% para Retenciones, se aplica el 6% para Percepciones.
        Returns: (aliquot_ret, aliquot_per)
        """
        aliquot_ret = 5.0
        aliquot_per = 6.0
        is_aliquot_castigo = True
        try:
            # Decode binary field to bytes
            file_content = base64.b64decode(self.file_padron)
            # Convert bytes to string
            csv_text = file_content.decode("latin-1")
            # Split by lines and process
            for line in csv_text.split('\n'):
                if not line:
                    continue
                values = line.split(";")
                # CUIT is at index 3, compare as strings
                if len(values) > 8 and values[3] == cuit:
                    # Percepción at index 7, Retención at index 8
                    per_str = values[7] if len(values) > 7 else "0"
                    ret_str = values[8] if len(values) > 8 else "0"
                    # Convert to float, handling comma as decimal separator
                    aliquot_per = float(per_str.replace(",", "."))
                    aliquot_ret = float(ret_str.replace(",", "."))
                    is_aliquot_castigo = False
                    break
        except Exception as e:
            raise UserError(_("Error reading PARP data for CUIT %s: %s") % (cuit, str(e)))
        return is_aliquot_castigo, aliquot_ret, aliquot_per

    def find_file(self, rootdir, type_code):
        res = False
        date = str(self.l10n_ar_padron_from_date.month) + \
            str(self.l10n_ar_padron_from_date.year)
        pattern = "%s.{1}|.TXT\Z" % type_code + date
        for subdir, dirs, files in os.walk(rootdir):
            for f in files:
                if re.search(pattern, f):
                    res = f
                    break
        return res

    def _get_aliquit(self, partner):
        nro = False
        aliquot_ret = 0.0
        aliquot_per = 0.0

        # Check if this is Santa Fe PARP format
        if self._is_santa_fe_jurisdiction():
            # Read PARP directly from binary field
            is_aliquot_castigo, aliquot_ret, aliquot_per = self._read_parp_from_binary(partner.vat)
            return is_aliquot_castigo, aliquot_ret, aliquot_per
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
