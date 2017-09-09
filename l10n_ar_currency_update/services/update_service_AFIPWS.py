# -*- coding: utf-8 -*-
# © 2009 Camptocamp
# © 2009 Grzegorz Grzelak
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.currency_rate_update import services

import logging
_logger = logging.getLogger(__name__)


class AFIPWSGetter(services.currency_getter_interface.CurrencyGetterInterface):
    code = 'afip_ws'
    name = 'AFIP WS'

    supported_currency_array = [
        'USD', 'EUR', 'AUD', 'CAD', 'GBP', 'JPY', 'MXN', 'UYU', 'VEF']
