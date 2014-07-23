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
from openerp.tools.translate import _
import re
import logging

_logger = logging.getLogger(__name__)

class partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
        'property_wsafip_puc': fields.property('wsafip.connection',
                                               type='many2one',
                                               relation='wsafip.connection',
                                               string='PUC connection',
                                               method=True,
                                               view_load=True,
                                               group_name='WSAFIP Connections'),
    }

    def update_from_wsafip(self, cr, uid, ids, default=None, context=None):
        default = default or {}
        for par in self.browse(cr, uid, ids):
            conn = par.property_wsafip_puc
            conn.server_id.wspuc_get_contribuyente(conn.id, par.name)
            import pdb; pdb.set_trace()
        return

partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
