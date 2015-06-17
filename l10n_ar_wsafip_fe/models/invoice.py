# -*- coding: utf-8 -*-
import logging
from pyi25 import PyI25
from openerp import fields, models, api, _
from openerp.exceptions import Warning
from cStringIO import StringIO as StringIO
_logger = logging.getLogger(__name__)


class invoice(models.Model):
    _inherit = "account.invoice"

# TODO ver si implementamos el afip result
    # afip_result = fields.Selection(
    #     [('', 'No CAE'), ('A', 'Accepted'),
    #      ('R', 'Rejected'), ('O', 'Observed')],
    #     'Status',
    #     default="",
    #     copy=False,
    #     help='This state is asigned by the AFIP. If * No CAE * state mean you\
    #     have no generate this invoice by ')
    afip_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True
        )
    afip_cae = fields.Char(
        copy=False,
        string='CAE number',
        readonly=True,
        size=24
        )
    afip_cae_due = fields.Date(
        copy=False,
        readonly=True,
        string='CAE due Date',
        )
# TODO ver si implementamos el error id
    # afip_error_id = fields.Many2one(
    #     'afip.wsfe_error',
    #     'AFIP Status',
    #     copy=False,
    #     readonly=True)
    afip_barcode = fields.Char(
        compute='_get_barcode',
        string='AFIP Barcode'
        )
    afip_barcode_img = fields.Binary(
        compute='_get_barcode',
        string='AFIP Barcode Image'
        )

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
    def get_related_invoices_data(self):
        """
        List related invoice information to fill CbtesAsoc.
        # TODO mejorar y buscar la relacion por un m2o y no por origin
        """
        res = {}
        for invoice in self:
            rel_invoices_data = []
            rel_invoices = self.search([
                ('number', '=', self.origin),
                ('state', 'not in',
                    ['draft', 'proforma', 'proforma2', 'cancel'])])
            for rel_inv in rel_invoices:
                rel_invoices_data.append({
                    'Tipo': rel_inv.afip_document_class_id.afip_code,
                    'PtoVta': rel_inv.point_of_sale,
                    'Nro': rel_inv.invoice_number,
                })
            res[invoice.id] = rel_invoices_data
        return res

    @api.multi
    def action_cancel(self):
        for inv in self:
            if self.afip_cae:
                raise Warning(
                    _('Error! You can not cancel an electronic invoice (has CAE assigned).\
                    You should do a credit note instead.'))
        return super(invoice, self).action_cancel()

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
                # TODO agregar la cotizacion en un campo de la factura y utilizar ese para hacer el asiento
                'MonCotiz': inv.currency_id.compute(
                    1.,
                    inv.company_id.currency_id),
                'CbtesAsoc': {'CbteAsoc': inv.get_related_invoices_data()[inv.id]},
                'Tributos': {
                    'Tributo': [{
                        'Id': x.tax_code_id.afip_code,
                        'Desc': x.tax_code_id.name,
                        'BaseImp': x.base_amount,
                        'Importe': x.tax_amount} for x in self.not_vat_tax_ids]},
                'Iva': {
                    'AlicIva': [{
                        'Id': x.tax_code_id.afip_code,
                        'BaseImp': x.base_amount,
                        'Importe': x.tax_amount} for x in self.vat_tax_ids]},
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
                    raise Warning(_('AFIP Validation Error. %s' % msg))
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
