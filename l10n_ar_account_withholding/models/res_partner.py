# -*- coding: utf-8 -*-
from openerp import models, fields, api
# from pyafipws.padron import PadronAFIP
import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    arba_alicuot_ids = fields.One2many(
        'res.partner.arba_alicuot',
        'partner_id',
        'Alicuotas de ARBA'
    )
    drei = fields.Selection([
        ('activo', 'Activo'),
        ('no_activo', 'No Activo'),
    ],
        string='DREI',
    )
    default_regimen_ganancias_id = fields.Many2one(
        'afip.tabla_ganancias.alicuotasymontos',
        'Regimen Ganancias por Defecto',
    )

    @api.multi
    def get_arba_alicuota_percepcion(self):
        company = self._context.get('invoice_company')
        invoice_date = self._context.get('invoice_date')
        if invoice_date and company:
            date = datetime.strptime(invoice_date, '%Y-%m-%d')
            arba = self.get_arba_data(company, date)
            return arba.alicuota_percepcion / 100.0
        return 0

    @api.multi
    def get_arba_alicuota_retencion(self, company, date):
        arba = self.get_arba_data(company, date)
        return arba.alicuota_retencion / 100.0

    @api.multi
    def get_arba_data(self, company, date):
        self.ensure_one()
        from_date = (date + relativedelta(day=1)).strftime('%Y%m%d')
        to_date = (date + relativedelta(
            day=1, days=-1, months=+1)).strftime('%Y%m%d')
        commercial_partner = self.commercial_partner_id
        arba = self.arba_alicuot_ids.search([
            ('from_date', '=', from_date),
            ('to_date', '=', to_date),
            ('company_id', '=', company.id),
            ('partner_id', '=', commercial_partner.id)], limit=1)
        if not arba:
            arba_data = company.get_arba_data(
                commercial_partner,
                from_date, to_date,
            )
            arba_data['partner_id'] = commercial_partner.id
            arba_data['company_id'] = company.id
            arba = self.arba_alicuot_ids.sudo().create(arba_data)
        return arba


class ResPartnerArbaAlicuot(models.Model):
    _name = "res.partner.arba_alicuot"

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        ondelete='cascade',
    )
    from_date = fields.Date(
    )
    to_date = fields.Date(
    )
    numero_comprobante = fields.Char(
    )
    codigo_hash = fields.Char(
    )
    alicuota_percepcion = fields.Float(
    )
    alicuota_retencion = fields.Float(
    )
    grupo_percepcion = fields.Char(
    )
    grupo_retencion = fields.Char(
    )
