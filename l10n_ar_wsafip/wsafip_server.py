# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class wsafip_server(osv.osv):
    _name = "wsafip.server"

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'class'], context=context)
        res = []
        for record in reads:
            res.append((record['id'], u"{name} [{class}]".format(**record)))
        return res

    _columns = {
        'name': fields.char('Name', size=64, select=1),
        'code': fields.char('Code', size=16, select=1),
        'class': fields.selection([('production', 'Production'), ('homologation', 'Homologation')], 'Class'),
        'url': fields.char('URL', size=512),
        'auth_conn_id': fields.one2many('wsafip.connection', 'logging_id', 'Authentication Connections'),
        'conn_id': fields.one2many('wsafip.connection', 'server_id', 'Service Connections'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
