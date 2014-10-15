# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from openerp.osv import osv
from openerp.osv.orm import browse_null
import re
import logging
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)

# Number Filter
re_number = re.compile(r'\d{8}')

# Functions to list parents names.


def _get_parents(child, parents=[]):
    if child and not isinstance(child, browse_null):
        return parents + [child.name] + _get_parents(child.parent_id)
    else:
        return parents


def _calc_concept(product_types):
    if product_types == set(['consu']):
        concept = '1'
    elif product_types == set(['product']):
        concept = '1'
    elif product_types == set(['consu', 'product']):
        concept = '1'
    elif product_types == set(['service']):
        concept = '2'
    elif product_types == set(['consu', 'service']):
        concept = '3'
    elif product_types == set(['product', 'service']):
        concept = '3'
    elif product_types == set(['consu', 'product', 'service']):
        concept = '3'
    else:
        concept = False
    return concept


class invoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends(
        'invoice_line',
        'invoice_line.product_id',
        'invoice_line.product_id.type',
    )
    def _get_concept(self):
        product_types = set(
            [line.product_id.type for line in self.invoice_line])
        self.afip_concept = _calc_concept(product_types)

    afip_concept = fields.Selection(
        compute='_get_concept',
        selection=[('1', 'Consumible'),
                   ('2', 'Service'),
                   ('3', 'Mixed')],
        string="AFIP concept",)
    afip_result = fields.Selection(
        [('', 'No CAE'), ('A', 'Accepted'),
         ('R', 'Rejected'), ('O', 'Observed')],
        'Status',
        default="",
        copy=False,
        help='This state is asigned by the AFIP. If * No CAE * state mean you\
        have no generate this invoice by ')
    afip_service_start = fields.Date(
        string='Service Start Date')
    afip_service_end = fields.Date(
        string='Service End Date')
    afip_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True)
    afip_cae = fields.Char(
        copy=False,
        string='CAE number',
        size=24)
    afip_cae_due = fields.Date(
        copy=False,
        string='CAE due Date')
    afip_error_id = fields.Many2one(
        'afip.wsfe_error',
        'AFIP Status',
        copy=False,
        readonly=True)

    @api.multi
    def action_cancel(self):
        for inv in self:
            if self.afip_cae:
                raise osv.except_orm(
                    _('Error!'),
                    _('Cancellation of electronic invoices is not implemented yet.'))
        return super(invoice, self).action_cancel()

    @api.one
    def get_related_invoices(self):
        """
        List related invoice information to fill CbtesAsoc
        """
        res = []
        rel_invoices = self.search([
            ('number', '=', self.origin),
            ('state', 'not in',
                ['draft', 'proforma', 'proforma2', 'cancel'])])
        for rel_inv in rel_invoices:
            journal = rel_inv.journal_id
            res.append({
                'Tipo': rel_inv.afip_document_class_id.afip_code,
                'PtoVta': journal.point_of_sale,
                'Nro': rel_inv.number,
            })
        return res

    @api.one
    def get_taxes(self):
        res = []
        for tax in self.tax_line:
            if tax.tax_code_id:
                if tax.tax_code_id.vat_tax:
                    continue
                else:
                    res.append({
                        'Id': tax.tax_code_id.parent_afip_code,
                        'Desc': tax.tax_code_id.name,
                        'BaseImp': tax.base_amount,
                        'Alic': (tax.tax_amount / tax.base_amount),
                        'Importe': tax.tax_amount,
                    })
            else:
                raise Warning(_('TAX without tax-code!\
                     Please, check if you set tax code for invoice or \
                     refund on tax %s.') % tax.name)
        return res

    @api.one
    def get_vat(self):
        res = []
        for tax in self.tax_line:
            if tax.tax_code_id:
                if not tax.tax_code_id.vat_tax:
                    continue
                else:
                    res.append({
                        'Id': tax.tax_code_id.parent_afip_code,
                        'BaseImp': tax.base_amount,
                        'Importe': tax.tax_amount,
                    })
            else:
                raise Warning(_('TAX without tax-code!\
                     Please, check if you set tax code for invoice or \
                     refund on tax %s.') % tax.name)
        return res

    @api.multi
    def action_number(self):
        self.action_retrieve_cae()
        res = super(invoice, self).action_number()
        return res

    @api.multi
    def action_retrieve_cae(self):
        """
        Contact to the AFIP to get a CAE number.
        """
        conn_obj = self.env['wsafip.connection']

        Servers = {}
        Requests = {}
        Inv2id = {}
        for inv in self:
            journal = inv.journal_id
            document_class = inv.afip_document_class_id
            conn = inv.journal_document_class_id.afip_connection_id

            # Ignore invoices with cae
            if inv.afip_cae and inv.afip_cae_due:
                continue

            # Only process if set to connect to afip
            if not conn:
                continue

            # Ignore invoice if connection server is not type WSFE.
            if conn.server_id.code != 'wsfe':
                continue

            Servers[conn.id] = conn.server_id.id

            # Take the last number of the "number".
            invoice_number = inv.next_invoice_number

            _f_date = lambda d: d and d.replace('-', '')

            # Build request dictionary
            if conn.id not in Requests:
                Requests[conn.id] = {}
            Requests[conn.id][inv.id] = dict((k, v) for k, v in {
                'CbteTipo': document_class.afip_code,
                'PtoVta': journal.point_of_sale,
                'Concepto': inv.afip_concept,
                'DocTipo': inv.partner_id.document_type_id.afip_code or '99',
                'DocNro': int(inv.partner_id.document_type_id.afip_code is not None and inv.partner_id.document_number),
                'CbteDesde': invoice_number,
                'CbteHasta': invoice_number,
                'CbteFch': _f_date(inv.date_invoice),
                'ImpTotal': inv.amount_total,
                # TODO: Averiguar como calcular el Importe Neto no Gravado
                'ImpTotConc': 0,
                'ImpNeto': inv.amount_untaxed,
                # TODO cambiar la funcion de estos campos
                # ESTE SON LOS QUE NO TIENEN IMPUESTOS, estan exentos
                'ImpOpEx': inv.exempt_amount,
                # 'ImpOpEx': inv.compute_all(line_filter=lambda line: len(line.invoice_line_tax_id) == 0)['amount_total'],
                # ESTE TIENE QUE SER CON TODOS LOS IMPUESTOS QUE SEAN VAT
                'ImpIVA': inv.vat_amount,
                # 'ImpIVA': inv.compute_all(tax_filter=lambda tax: 'IVA' in _get_parents(tax.tax_code_id))['amount_tax'],
                # ESTE TIENE QUE SER CON TODOS LOS IMPUESTOS QUE NO SEAN VAT
                'ImpTrib': inv.other_taxes_amount,
                # 'ImpTrib': inv.compute_all(tax_filter=lambda tax: 'IVA' not in _get_parents(tax.tax_code_id))['amount_tax'],

                'FchServDesde': _f_date(inv.afip_service_start) if inv.afip_concept != '1' else None,
                'FchServHasta': _f_date(inv.afip_service_end) if inv.afip_concept != '1' else None,
                'FchVtoPago': _f_date(inv.date_due) if inv.afip_concept != '1' else None,
                'MonId': inv.currency_id.afip_code,
                'MonCotiz': inv.currency_id.compute(
                    1.,
                    inv.company_id.currency_id),
                'CbtesAsoc': {'CbteAsoc': inv.get_related_invoices()[0]},
                'Tributos': {'Tributo': inv.get_taxes()[0]},
                'Iva': {'AlicIva': inv.get_vat()[0]},
                # TODO implementar los optionals
                'Opcionales': {},
            }.iteritems() if v is not None)
            Inv2id[invoice_number] = inv.id
        print 'Requests', Requests
        for c_id, req in Requests.iteritems():
            res = conn_obj.browse(c_id).server_id.wsfe_get_cae(c_id, req)
            for k, v in res.iteritems():
                if 'CAE' in v:
                    self.browse(Inv2id[k]).write({
                        'afip_cae': v['CAE'],
                        'afip_cae_due': v['CAEFchVto'],
                    })
                else:
                    # Muestra un mensaje de error por la factura con error.
                    # Se cancelan todas las facturas del batch!
                    msg = 'Factura %s:\n' % k + '\n'.join(
                        [u'(%s) %s\n' % e for e in v['Errores']] +
                        [u'(%s) %s\n' % e for e in v['Observaciones']]
                    )
                    raise osv.except_osv(_(u'AFIP Validation Error'), msg)

        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
