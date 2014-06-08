# -*- coding: utf-8 -*-
##############################################################################
#
#    Sistemas ADHOC - ADHOC SA
#    https://launchpad.net/~sistemas-adhoc
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)

class argentinian_base_configuration(osv.osv_memory):
    _inherit = 'argentinian.base.config.settings'

    _columns = {
        'module_l10n_ar_aeroo_invoice': fields.boolean('Aeroo Invoice Report',
            help = """Installs the l10n_ar_aeroo_invoice module."""),
        'module_l10n_ar_aeroo_remit': fields.boolean('Aeroo Remit Report',
            help = """Installs the l10n_ar_aeroo_remit module."""),
        'module_l10n_ar_aeroo_purchase': fields.boolean('Aeroo Purchase Reports',
            help = """Installs the l10n_ar_aeroo_purchase module."""),
        'module_l10n_ar_aeroo_sale': fields.boolean('Aeroo Sale Reports',
            help = """Installs the l10n_ar_aeroo_sale module."""),
        'module_l10n_ar_aeroo_receipt': fields.boolean('Aeroo Receipt Report',
            help = """Installs the l10n_ar_aeroo_receipt module."""),
    }        
    
    _defaults = {
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
