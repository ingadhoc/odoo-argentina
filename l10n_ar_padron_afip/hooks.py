# -*- coding: utf-8 -*-
# Copyright 2017 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def post_init_hook(cr, registry):
    """
    Try to sync data from padron
    """
    account_config = registry['account.config.settings']
    account_config_id = account_config.create(
        cr, 1, {})
    try:
        account_config.refresh_taxes_from_padron(cr, 1, account_config_id)
        account_config.refresh_concepts_from_padron(cr, 1, account_config_id)
        account_config.refresh_activities_from_padron(cr, 1, account_config_id)
    except:
        pass
