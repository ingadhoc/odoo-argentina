from odoo import SUPERUSER_ID, api
from odoo.tools import parse_version


def migrate(cr, version):
    # TODO when migrating to 20.0: move this script to the 20.0 version folder and also skip 19.0.1.14.0+
    # 18.0.1.16.0 already applied this fix: running it again would override companies that enabled it back on purpose
    if parse_version("18.0.1.16.0") <= parse_version(version) < parse_version("19.0"):
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company"]._l10n_ar_ux_hide_invoice_tax_company_currency()
