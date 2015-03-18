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


class invoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends(
        'invoice_line',
        'invoice_line.product_id',
        'invoice_line.product_id.type',
        'journal_document_class_id.afip_connection_id',
    )
    def _get_concept(self):
        afip_concept = False
        # If document has no connection then it is not electronic
        if self.journal_document_class_id.afip_connection_id:
            product_types = set(
                [line.product_id.type for line in self.invoice_line if line.product_id])
            consumible = set(['consu', 'product'])
            service = set(['service'])
            mixed = set(['consu', 'service', 'product'])
            if product_types.issubset(mixed):
                afip_concept = '3'
            if product_types.issubset(service):
                afip_concept = '2'
            if product_types.issubset(consumible):
                afip_concept = '1'
        self.afip_concept = afip_concept

    afip_concept = fields.Selection(
        compute='_get_concept',
        selection=[('1', 'Consumible'),
                   ('2', 'Service'),
                   ('3', 'Mixed')],
        string="AFIP concept",)
# TODO ver si implementamos el afip result
    # afip_result = fields.Selection(
    #     [('', 'No CAE'), ('A', 'Accepted'),
    #      ('R', 'Rejected'), ('O', 'Observed')],
    #     'Status',
    #     default="",
    #     copy=False,
    #     help='This state is asigned by the AFIP. If * No CAE * state mean you\
    #     have no generate this invoice by ')
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
        readonly=True,
        size=24)
    afip_cae_due = fields.Date(
        copy=False,
        readonly=True,
        string='CAE due Date',)
# TODO ver si implementamos el error id
    # afip_error_id = fields.Many2one(
    #     'afip.wsfe_error',
    #     'AFIP Status',
    #     copy=False,
    #     readonly=True)
    afip_barcode = fields.Char(
        compute='_get_barcode',
        string='AFIP Barcode')
    afip_barcode_img = fields.Binary(
        compute='_get_barcode',
        string='AFIP Barcode')

    @api.one
    @api.depends('afip_cae')
    def _get_barcode(self):
        barcode = False
        if self.afip_cae:
            cae_due = ''.join(
                [c for c in str(self.afip_cae_due or '') if c.isdigit()])
            barcode = ''.join([str(self.company_id.partner_id.vat[2:]),
                               "%02d" % int(self.afip_document_class_id.afip_code),
                               "%04d" % int(self.journal_id.point_of_sale),
                               str(self.afip_cae), cae_due])
            barcode = barcode + self.verification_digit_modulo10(barcode)
        self.afip_barcode = barcode

        "Generate the required barcode Interleaved of 7 image using PIL"
        image = False
        if barcode:
            from pyi25 import PyI25
            from cStringIO import StringIO as StringIO
            # create the helper:
            pyi25 = PyI25()
            output = StringIO()
            # call the helper:
            bars = ''.join([c for c in barcode if c.isdigit()])
            if not bars:
                bars = "00"
            pyi25.GenerarImagen(bars, output, extension="PNG")
            # get the result and encode it for openerp binary field:
            image = output.getvalue()
            image = output.getvalue().encode("base64")
            output.close()
        self.afip_barcode_img = image

    @api.model
    def verification_digit_modulo10(self, code):
        "Calculate the verification digit 'modulo 10'"
        # Step 1: sum all digits in odd positions, left to right
        code = code.strip()
        if not code or not code.isdigit():
            return ''
        etapa1 = sum([int(c) for i, c in enumerate(code) if not i % 2])
        # Step 2: multiply the step 1 sum by 3
        etapa2 = etapa1 * 3
        # Step 3: start from the left, sum all the digits in even positions
        etapa3 = sum([int(c) for i, c in enumerate(code) if i % 2])
        # Step 4: sum the results of step 2 and 3
        etapa4 = etapa2 + etapa3
        # Step 5: the minimun value that summed to step 4 is a multiple of 10
        digito = 10 - (etapa4 - (int(etapa4 / 10) * 10))
        if digito == 10:
            digito = 0
        return str(digito)

    @api.multi
    def action_cancel(self):
        for inv in self:
            if self.afip_cae:
                raise osv.except_orm(
                    _('Error!'),
                    _('You can not cancel an electronic invoice (has CAE assigned).\
                    You should do a credit note instead.'))
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
            afip_document_number = rel_inv.afip_document_number.split('-')
            try:
                afip_document_number = int(afip_document_number[1])
            except:
                raise Warning(_('Error getting related document number'))
            res.append({
                'Tipo': rel_inv.afip_document_class_id.afip_code,
                'PtoVta': journal.point_of_sale,
                'Nro': afip_document_number,
            })
        return res

    @api.one
    def get_taxes(self):
        res = []
        for tax in self.tax_line:
            if tax.tax_code_id:
                if tax.tax_code_id.parent_id.name == 'IVA':
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
                if tax.tax_code_id.parent_id.name != 'IVA':
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
                'DocTipo': inv.commercial_partner_id.document_type_id.afip_code or '99',
                'DocNro': int(inv.commercial_partner_id.document_type_id.afip_code is not None and inv.commercial_partner_id.document_number),
                'CbteDesde': invoice_number,
                'CbteHasta': invoice_number,
                'CbteFch': _f_date(inv.date_invoice),
                'ImpTotal': inv.amount_total,
                # TODO: Averiguar como calcular el Importe Neto no Gravado
                'ImpTotConc': 0,
                'ImpNeto': inv.amount_untaxed,
                'ImpOpEx': inv.exempt_amount,
                'ImpIVA': inv.vat_amount,
                'ImpTrib': inv.other_taxes_amount,
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
