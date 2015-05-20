# -*- coding: utf-8 -*-
from openerp import fields, api, models


class wsafip_server(models.Model):
    _name = "wsafip.server"

    @api.multi
    def name_get(self):
        reads = self.read(['name', 'type'])
        res = []
        for record in reads:
            res.append((record['id'], u"{name} [{type}]".format(**record)))
        return res

    name = fields.Char(
        'Name',
        required=True,
        )
    code = fields.Char(
        'Code',
        required=True,
        )
    type = fields.Selection(
        [('production', 'Production'), ('homologation', 'Homologation')],
        'Type',
        required=True,
        )
    url = fields.Char(
        'URL',
        required=True,
        )
    auth_conn_ids = fields.One2many(
        'wsafip.connection',
        'logging_id',
        'Authentication Connections'
        )
    conn_id = fields.One2many(
        'wsafip.connection',
        'server_id',
        'Service Connections'
        )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
