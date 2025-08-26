import base64
import logging
import os
import re
import tempfile
import zipfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

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
    file_padron_fname = fields.Char(
        "Filename",
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
        agip_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_901')
        implemented_tag = arba_tag | agip_tag
        for rec in self:
            if rec.jurisdiction_id not in implemented_tag:
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

        ext = self.file_padron_fname.split('.')[-1].lower()

        if ext == 'zip':
            with zipfile.ZipFile(fname, 'r') as zip_file:
                zip_file.extractall(path=ruta_extraccion)
                zip_file.close()
        elif ext == 'rar':
            """
            # version 2 (not working)
            import rarfile
            with rarfile.RarFile(fname) as rar_file:
                rarfile.is_rarfile(fname)
                extracted_file_name = rar_file.namelist()[0]
                rar_file.extractall(path=ruta_extraccion)
                rar_file.close()
            """
            # version 3 working but when reading file UnicodeDecodeError: 'utf-8' codec
            # can't decode byte 0xac in position 1164: invalid start byte
            import shutil
            import subprocess
            #   2. Verifica que bsdtar esté instalado
            if not shutil.which("bsdtar"):
                raise UserError(_("La herramienta 'bsdtar' no está instalada en el sistema."))

            # 3. Ejecuta bsdtar con subprocess
            result = subprocess.run(
                ["bsdtar", "-xf", fname, "-C", ruta_extraccion],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if result.returncode != 0:
                raise UserError(_("Error al descomprimir el archivo RAR:\n%s") % result.stderr.decode())


        else:
            raise UserError(_('No se puede descomprimir este tipo de archivo'))

    def find_aliquot(self, path, cuit):
        """We try to find aliqut and number for a partner given
        """
        agip_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_901')
        arba_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_902')
        cdba_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_904')

        if self.jurisdiction_id == arba_tag:
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
        if self.jurisdiction_id == agip_tag:
            import csv
            with open(path, encoding="ISO-8859-1", newline='') as csvfile:
                """ Ejemplo de registro: [
                    'ï»¿22112018',  0 Fecha Padron
                    '01122018',     1 Fecha desde
                    '31122018',     2 Fecha Hasta
                    '20000163989',  3 CUIT
                    'D',            4
                    'S',            5
                    'N',            6
                    '0,00',         7 alicuota percepcion
                    '0,00',         8 alicuota retencion
                    '00',
                    '00',
                    'ETCHEVERRIGARAY JUAN  CARLOS']
                """
                rowCount = 0
                # to avoid error "CSV.Error: Line Contains Null Byte in Python" with some txt files
                csvfile = (row.replace('\0', '') for row in csvfile)
                for row in csv.reader(csvfile, delimiter='\n'):
                    row = row[0].split(';')
                    file_row_cuit = row[3]
                    if cuit != file_row_cuit:
                        continue

                    if rowCount == 0 and row[1] != self.l10n_ar_padron_from_date.strftime('%d%m%Y'):
                        _logger.info(_("AGIP: El archivo no corresponde al periodo consultado %s != %s" %
                            (row[1], self.l10n_ar_padron_from_date.strftime('%d%m%Y'))))
                        return False

                    return 'Alicuota de Padron', {
                        'alicuota_percepcion': float(row[7].replace(',', '.')),
                        'alicuota_retencion': float(row[8].replace(',', '.')),
                    }

        if self.jurisdiction_id == cdba_tag:
            # TODO
            pass

    def find_file(self, rootdir, type_code):
        res = False
        date = str(self.l10n_ar_padron_from_date.month) + \
            str(self.l10n_ar_padron_from_date.year)
        pattern = r"%s.{1}|.TXT\Z" % type_code + date
        for subdir, dirs, files in os.walk(rootdir):
            for f in files:
                if re.search(pattern, f):
                    res = f
                    break
        return res

    def _get_aliquit(self, partner):
        agip_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_901')
        arba_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_902')
        cdba_tag = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_904')

        if self.jurisdiction_id == arba_tag:
            padron_types = ["Per", "Ret"]
        elif self.jurisdiction_id == agip_tag:
            padron_types = ["AR"]
            econding = "UTF-8"
            # padron_types = [f"ARDJU008{self.l10n_ar_padron_to_date.month:02d}{self.l10n_ar_padron_to_date.year}.txt"]
        elif self.jurisdiction_id == cdba_tag:
            padron_types = ["Régimen de retención.txt", "Régimen de percepción.txt"]

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
            elif padron_type == "Ret":
                aliquot_ret = aliquot and aliquot.replace(",", ".")
            elif padron_type == "AR":
                aliquot_per = aliquot and aliquot.get('alicuota_percepcion').replace(",", ".")
                aliquot_ret = aliquot and aliquot.get('alicuota_retencion').replace(",", ".")
        return nro, aliquot_ret, aliquot_per
