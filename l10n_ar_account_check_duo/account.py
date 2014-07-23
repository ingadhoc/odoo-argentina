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

from openerp.osv import osv, fields

class account_journal(osv.osv):
    _name = 'account.journal'
    _inherit = 'account.journal'
    _columns = {
        'use_issued_check': fields.boolean('Use Issued Checks', help='Allow to user Issued Checks in associated vouchers.'),
        'use_third_check': fields.boolean('Use Third Checks', help='Allow to user Third Checks in associated vouchers.'),
        'validate_only_checks': fields.boolean('Validate only Checks', help='If marked, when validating a voucher, verifies that the total amounth of the voucher is the same as the checks used.'),
    }

account_journal()
