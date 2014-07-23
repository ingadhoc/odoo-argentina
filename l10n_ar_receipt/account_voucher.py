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

from osv import osv, fields
import decimal_precision as dp
from tools.translate import _
import netsvc


class account_voucher(osv.osv):

  #Agrego el campo  Receipt a la clase Account voucher para generar los recibos

    _inherit = "account.voucher"
    _columns = {
                'receipt_id':fields.many2one('receipt.receipt',string='Receipt',required=False,readonly=True,states={'draft':[('readonly',False)]}),

                #'proof_id':fields.many2one('proof',string='Payment Proof',required=False,readonly=True,states={'draft':[('readonly',False)]}),
               }

account_voucher()


