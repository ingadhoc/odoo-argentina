##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from . import wizard
from . import demo


def post_init_hook(env):
    env["res.company"]._l10n_ar_ux_hide_invoice_tax_company_currency()
