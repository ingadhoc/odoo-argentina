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

class product_uom(osv.osv):
    
    _name = 'product.uom'
    _inherit = "product.uom"
    _columns = {
        'afip_code': fields.integer('UoM AFIP Code', size=2, required=True),
    }
    
    #wsfex_update_uom <-- se actualiza mediante esa funcion en wsafip_server

product_uom()
