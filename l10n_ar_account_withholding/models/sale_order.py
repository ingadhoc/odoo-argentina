# -*- coding: utf-8 -*-
from openerp import models, api, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _amount_all(self):
        """
        Hacemos esto para disponer de fecha del pedido y cia para calcular
        impuesto con código python (por ej. para ARBA).
        Aparentemente no se puede cambiar el contexto a cosas que se llaman
        desde un onchange (ver https://github.com/odoo/odoo/issues/7472)
        entonces usamos este artilugio
        """
        date_order = self.date_order or fields.Date.context_today(self)
        self.env.context.date_invoice = date_order
        self.env.context.invoice_company = self.company_id
        return super(SaleOrder, self)._amount_all()
