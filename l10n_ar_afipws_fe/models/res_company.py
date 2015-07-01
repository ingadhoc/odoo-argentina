# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from openerp.exceptions import Warning


class res_company(models.Model):

    _inherit = "res.company"

    @api.multi
    def wsfe_get_status(self):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento de
        infraestructura (FEDummy)
        """
        self.get_connection('wsfe').wsfe_get_status()
