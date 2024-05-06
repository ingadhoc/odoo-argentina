# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID
from . import models


def _l10n_ar_pos_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    if env.ref('base.module_l10n_ar_pos').demo:
        company_ri = env.ref('l10n_ar.company_ri').id
        env['pos.config'].with_context(allowed_company_ids=[company_ri]).create({'name': 'Argentinean Shop'})
        env['pos.config'].post_install_pos_localisation(company_ri)
