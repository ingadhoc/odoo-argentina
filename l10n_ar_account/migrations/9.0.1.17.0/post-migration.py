# -*- coding: utf-8 -*-
from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    # now that we have account_fix as depend we fix previous invoices
    env['account.invoice'].search(
        [('type', 'in', ['in_refund', 'out_refund'])]).compute_taxes()
