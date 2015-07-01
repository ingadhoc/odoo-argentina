# -*- coding: utf-8 -*-
from openerp import models, fields
import logging
_logger = logging.getLogger(__name__)


class wsafip_server(models.Model):
    _inherit = "wsafip.server"

    code = fields.Selection(
        selection_add=[('wsfe', 'Web Service de Factura Electrónica')]
        )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
