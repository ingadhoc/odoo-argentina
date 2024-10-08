from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
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
        for rec in self:
            if rec.jurisdiction_id != arba_tag:
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
        padron_types = ["Per", "Ret"]
        nro = False
        aliquot_ret = 0.0
        aliquot_per = 0.0
        for padron_type in padron_types:
            path_file = self.find_file("/tmp/", padron_type)
            if not path_file:
                self.descompress_file(self.file_padron)
                path_file = self.find_file("/tmp/", padron_type)
            nro, aliquot = self.find_aliquot("/tmp/" + path_file, partner.vat)
            if padron_type == "Per":
                aliquot_per = aliquot and aliquot.replace(",", ".")
            else:
                aliquot_ret = aliquot and aliquot.replace(",", ".")
        return nro, aliquot_ret, aliquot_per
