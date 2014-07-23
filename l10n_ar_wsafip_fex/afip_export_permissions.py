# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Elepe Servicios (http://www.elepeservicios.com.ar)
# All Rights Reserved
#
# Author : Dario Kevin De Giacomo (Elepe Servicios)
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

class afip_export_permissions(osv.osv):
    _name = "afip.export.permissions"
    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice ID'),
        'permission_code': fields.char('Codigo Despacho/Permiso de Embarque', size=16),
        'dst_merc': fields.many2one('res.country', 'Pais destino de la mercaderia', domain="[('afip_code','!=',None)]"),
        'valid_permission': fields.boolean('Valid Permission')
    }
            
afip_export_permissions()
