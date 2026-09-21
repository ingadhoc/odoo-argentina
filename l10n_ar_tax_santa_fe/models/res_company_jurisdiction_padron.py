import subprocess

from odoo import models
from odoo.addons.l10n_ar_tax.models.res_company_jurisdiction_padron import GREP_TIMEOUT

# PARP record layout (RG 37/2025 API Santa Fe, Annex I): position 40 is the contributor type,
# 'C' = Multilateral Agreement, 'D' = local.
PARP_CUIT_INDEX = 3
PARP_CONTRIBUTOR_TYPE_INDEX = 4
PARP_CONTRIBUTOR_MULTILATERAL = "C"


class ResCompanyJurisdictionPadron(models.Model):
    _inherit = "res.company.jurisdiction.padron"

    def _get_parp_contributor_type(self, cuit):
        """Contributor type ('C' / 'D') the PARP reports for the CUIT, False if not found."""
        self.ensure_one()
        if not cuit or not self._is_santa_fe_jurisdiction():
            return False
        path_file = self._ensure_parp_file_extracted()
        result = subprocess.run(
            ["grep", "-F", "-e", cuit, "--", path_file],
            capture_output=True,
            encoding="latin-1",
            timeout=GREP_TIMEOUT,
        )
        for line in result.stdout.splitlines():
            # grep also matches the CUIT inside other columns
            values = [value.strip() for value in line.split(";")]
            if len(values) > PARP_CONTRIBUTOR_TYPE_INDEX and values[PARP_CUIT_INDEX] == cuit:
                return values[PARP_CONTRIBUTOR_TYPE_INDEX].upper()
        return False
