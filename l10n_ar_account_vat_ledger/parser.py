##############################################################################
#
# Copyright (c) 2008-2011 Alistek Ltd (http://www.alistek.com) All Rights Reserved.
#                    General contacts <info@alistek.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This module is GPLv3 or newer and incompatible
# with OpenERP SA "AGPL + Private Use License"!
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from openerp.report import report_sxw
from lxml import etree

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        # model = self.pool.get(context['model'])
        model = self.pool.get(context['active_model'])
        print 'name', name
        print 'context', context
        
        
        # ids = context['ids']
        ids = context['active_ids']

        model_id = self.pool.get('ir.model').search(cr, uid, [('model','=',model._name)])
        if model_id:
            model_desc = self.pool.get('ir.model').browse(cr, uid, model_id[0], context).name
        else:
            model_desc = model._description

        result = model.fields_view_get(cr, uid, view_type='tree', context=context)
        fields_type = dict(map(lambda name: (name, result['fields'][name]['type']), result['fields']))
        fields_order = self._parse_string(result['arch'])
        rows = model.read(cr, uid, ids, context=context)
        print 'rows', rows

        self.localcontext.update({
            # 'screen_fields': fields_order,
            # 'screen_fields_type': fields_type,
            'screen_rows': rows,
            # 'screen_model': context['model'],
            # 'screen_title': model_desc,
          
        })

    def _parse_node(self, root_node):
        result = []
        for node in root_node:
            if node.tag == 'field':
                result.append(node.get('name'))
            else:
                result.extend(self._parse_node(node))
        return result

    def _parse_string(self, view):
        try:
            dom = etree.XML(view.encode('utf-8'))
        except:
            dom = etree.XML(view)   
        return self._parse_node(dom)

