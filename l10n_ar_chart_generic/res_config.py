# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2012 OpenERP - Team de Localización Argentina.
# https://launchpad.net/~openerp-l10n-ar-localization
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

class account_config_settings(osv.osv_memory):
    _name = 'account.config.settings'
    _inherit = 'account.config.settings'

    _columns = {
        'module_l10n_ar_invoice': fields.boolean('Argentine Basic Invoice',
                help="""Basic invoce data, logic and printing for Argentine.
                This installs the module l10n_ar_invoice"""),
        'module_l10n_ar_wsafip_fe': fields.boolean('Argentine Electronic Invoice',
                help="""Enable invoices to be generated using AFIP web services.
                This installs the module l10n_ar_wsafip_fe"""),
        'module_l10n_ar_bank': fields.boolean('Argentine Banks',
                help="""Complete the bank database, and let you complete the argentine bank list using BNA list by internet.
                This install the module l10n_ar_banks"""),
    }

    _defaults= {
    }

account_config_settings()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
