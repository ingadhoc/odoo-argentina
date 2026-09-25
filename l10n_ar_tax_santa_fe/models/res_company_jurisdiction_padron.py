import subprocess

from odoo import models
from odoo.addons.l10n_ar_tax.models.res_company_jurisdiction_padron import GREP_TIMEOUT

# Posición 40 del diseño de registro del PARP (RG 37/2025 de API Santa Fe, Anexo I):
# 'C' = Convenio Multilateral, 'D' = Local Santa Fe. Es la columna E del archivo, o sea el
# índice 4 del split por ';', y el CUIT es el índice 3.
PARP_CUIT_INDEX = 3
PARP_CONTRIBUTOR_TYPE_INDEX = 4
PARP_CONTRIBUTOR_MULTILATERAL = "C"


class ResCompanyJurisdictionPadron(models.Model):
    _inherit = "res.company.jurisdiction.padron"

    def _get_parp_contributor_type(self, cuit):
        """Tipo de contribuyente que el PARP informa para un CUIT ('C' / 'D'), o False si
        no figura en el padrón o la jurisdicción no es Santa Fe.

        La lectura de la alícuota descarta esta columna y no la tocamos: buscarla acá con
        grep -F (en C) es más barato que un segundo recorrido del archivo en Python, que es
        como está leído el padrón. El archivo ya quedó extraído por la propia lectura de la
        alícuota.
        """
        self.ensure_one()
        if not cuit or not self._is_santa_fe_jurisdiction():
            return False
        path_file = self._ensure_parp_file_extracted()
        result = subprocess.run(
            ["grep", "-F", cuit, path_file],
            capture_output=True,
            # El padrón viene en latin-1 y las razones sociales traen acentos: con el
            # encoding por defecto la salida del grep no se puede decodificar.
            encoding="latin-1",
            timeout=GREP_TIMEOUT,
        )
        for line in result.stdout.splitlines():
            # La comparación exacta por columna descarta los falsos positivos del grep (el
            # CUIT como substring de otro campo), igual que la lectura de la alícuota.
            values = [value.strip() for value in line.split(";")]
            if len(values) > PARP_CONTRIBUTOR_TYPE_INDEX and values[PARP_CUIT_INDEX] == cuit:
                return values[PARP_CONTRIBUTOR_TYPE_INDEX].upper()
        return False
