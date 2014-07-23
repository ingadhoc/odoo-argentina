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

class account_journal(osv.osv):
    _inherit = "account.journal"
    _columns = {
        'code': fields.char('Code', size=10, required=True,
                            help="The code will be used to generate the numbers of the journal entries of this journal."),
        'journal_class_id': fields.many2one('afip.journal_class', 'Document class'),
        'point_of_sale': fields.integer('Point of sale ID'),
    }
account_journal()

class res_currency(osv.osv):
    _inherit = "res.currency"
    _columns = {
        'afip_code': fields.char('AFIP Code', size=4),
    }
res_currency()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
