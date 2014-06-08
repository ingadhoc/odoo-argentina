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

class wsafip_server(osv.osv):
    _name = "wsafip.server"

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','class'], context=context)
        res = []
        for record in reads:
            res.append((record['id'], u"{name} [{class}]".format(**record)))
        return res

    _columns = {
        'name': fields.char('Name', size=64, select=1),
        'code': fields.char('Code', size=16, select=1),
        'class': fields.selection([('production','Production'),('homologation','Homologation')], 'Class'),
        'url': fields.char('URL', size=512),
        'auth_conn_id': fields.one2many('wsafip.connection','logging_id','Authentication Connections'),
        'conn_id': fields.one2many('wsafip.connection','server_id','Service Connections'),
    }

wsafip_server()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
