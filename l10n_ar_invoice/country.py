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

class afip_country(osv.osv):
    _inherit = 'res.country'

    _name = 'res.country'

    _columns = {
        'cuit_fisica': fields.char('CUIT persona fisica', size=11),
        'cuit_juridica': fields.char('CUIT persona juridica', size=11),
        'cuit_otro': fields.char('CUIT otro', size=11),
    }
afip_country()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
