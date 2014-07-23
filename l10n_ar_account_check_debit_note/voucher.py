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

import time
from lxml import etree

import netsvc
from osv import osv, fields
import decimal_precision as dp
from tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class account_voucher(osv.osv):
    
        
    # Modified
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        if context is None: context = {}
        _logger.info("context: %s",context)
        if view_type == 'form':
            if not view_id and context.get('invoice_type'):
                if context.get('invoice_type') in ('out_invoice', 'out_refund','out_debit'):
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
                else:
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
                result = result and result[1] or False
                view_id = result
            if not view_id and context.get('line_type'):
                if context.get('line_type') == 'customer':
                    _logger.info("customer: %s",view_id)
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
                    _logger.info("customer: %s",result)
                else:
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
                result = result and result[1] or False
                view_id = result

        res = super(account_voucher, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])

        if context.get('type', 'sale') in ('purchase', 'payment'):
            nodes = doc.xpath("//field[@name='partner_id']")
            for node in nodes:
                node.set('domain', "[('supplier', '=', True)]")
        res['arch'] = etree.tostring(doc)
        return res
        
    _inherit = "account.voucher"
    _description = 'Account voucher Debit Note'
    
    
    
account_voucher()    
    
