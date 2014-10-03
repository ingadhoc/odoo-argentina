# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from openerp.osv import osv
from openerp.osv.orm import browse_null
import re
import logging

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


class invoice_line(models.Model):
    """TODO borrar esto, usamos esta funcion solo apra el compute_all que tmb queremos borrar de la clase invoice"""
    _inherit = "account.invoice.line"
    def compute_all(self, cr, uid, ids, tax_filter=None, context=None):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        _tax_filter = tax_filter
        for line in self.browse(cr, uid, ids):
            _quantity = line.quantity
            _discount = line.discount
            _price = line.price_unit * (1-(_discount or 0.0)/100.0)
            _tax_ids = filter(_tax_filter, line.invoice_line_tax_id)
            taxes = tax_obj.compute_all(cr, uid,
                                        _tax_ids, _price, _quantity,
                                        product=line.product_id,
                                        partner=line.invoice_id.partner_id)

            _round = (lambda x: cur_obj.round(cr, uid, line.invoice_id.currency_id, x)) if line.invoice_id else (lambda x: x)
            res[line.id] = {
                'amount_untaxed': _round(taxes['total']),
                'amount_tax': _round(taxes['total_included'])-_round(taxes['total']),
                'amount_total': _round(taxes['total_included']), 
                'taxes': taxes['taxes'],
            }
        return res.get(len(ids)==1 and ids[0], res)

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


    def valid_batch(self, cr, uid, ids, *args):
        """
        Increment batch number groupping by afip connection server.
        """
        seq_obj = self.pool.get('ir.sequence')
        conns = []
        invoices = {}
        for inv in self.browse(cr, uid, ids):
            if not inv.journal_document_class_id:
                continue
            conn = inv.journal_document_class_id.afip_connection_id
            if not conn:
                continue
            if inv.journal_document_class_id.afip_items_generated + 1 != inv.journal_document_class_id.sequence_id.number_next:
                raise osv.except_osv(_(u'Syncronization Error'),
                                     _(u'La AFIP espera que el próximo número de secuencia sea %i, pero el sistema indica que será %i. Hable inmediatamente con su administrador del sistema para resolver este problema.') %
                                     (inv.journal_document_class_id.afip_items_generated + 1, inv.journal_document_class_id.sequence_id.number_next))
            conns.append(conn)
            invoices[conn.id] = invoices.get(conn.id, []) + [inv.id]

        for conn in conns:
            prefix = conn.batch_sequence_id.prefix or ''
            suffix = conn.batch_sequence_id.suffix or ''
            sid_re = re.compile('%s(\d*)%s' % (prefix, suffix))
            sid = seq_obj.next_by_id(cr, uid, conn.batch_sequence_id.id)
            self.write(cr, uid, invoices[conn.id], {
                'afip_batch_number': int(sid_re.search(sid).group(1)),
            })

        return True

    def get_related_invoices(self, cr, uid, ids, *args):
        """
        List related invoice information to fill CbtesAsoc
        """
        r = {}
        _ids = [ids] if isinstance(ids, int) else ids

        for inv in self.browse(cr, uid, _ids):
            r[inv.id] = []
            rel_inv_ids = self.search(cr, uid, [('number', '=', inv.origin),
                                                ('state', 'not in', ['draft', 'proforma', 'proforma2', 'cancel'])])
            for rel_inv in self.browse(cr, uid, rel_inv_ids):
                journal = rel_inv.journal_id
                r[inv.id].append({
                    'Tipo': rel_inv.journal_document_class_id.afip_document_class_id.afip_code,
                    'PtoVta': journal.point_of_sale,
                    'Nro': rel_inv.number,
                })

        return r[ids] if isinstance(ids, int) else r

    def get_taxes(self, cr, uid, ids, *args):
        r = {}
        _ids = [ids] if isinstance(ids, int) else ids

        for inv in self.browse(cr, uid, _ids):
            r[inv.id] = []

            for tax in inv.tax_line:
                #TODO, mejorar esto, muy feo y no se para que
                if tax.account_id.name == 'IVA a pagar':
                    continue
                if tax.tax_code_id:
                    r[inv.id].append({
                        'Id': tax.tax_code_id.parent_afip_code,
                        'Desc': tax.tax_code_id.name,
                        'BaseImp': tax.base_amount,
                        'Alic': (tax.tax_amount / tax.base_amount),
                        'Importe': tax.tax_amount,
                    })
                else:
                    raise osv.except_osv(_(u'TAX without tax-code'),
                                         _(u'Please, check if you set tax code for invoice or refund to tax %s.') % tax.name)

        return r[ids] if isinstance(ids, int) else r

    def get_vat(self, cr, uid, ids, *args):
        r = {}
        _ids = [ids] if isinstance(ids, int) else ids

        for inv in self.browse(cr, uid, _ids):
            r[inv.id] = []

            for tax in inv.tax_line:
                if tax.account_id.name != 'IVA a pagar':
                    continue
                r[inv.id].append({
                    'Id': tax.tax_code_id.parent_afip_code,
                    'BaseImp': tax.base_amount,
                    'Importe': tax.tax_amount,
                })

        return r[ids] if isinstance(ids, int) else r

    def get_optionals(self, cr, uid, ids, *args):
        optional_type_obj = self.pool.get('afip.optional_type')

        r = {}
        _ids = [ids] if isinstance(ids, int) else ids
        optional_type_ids = optional_type_obj.search(cr, uid, [])

        for inv in self.browse(cr, uid, _ids):
            r[inv.id] = []
            for optional_type in optional_type_obj.browse(cr, uid, optional_type_ids):
                if optional_type.apply_rule and optional_type.value_computation:
                    """
                    Debería evaluar apply_rule para saber si esta opción se computa
                    para esta factura. Y si se computa, se evalua value_computation
                    sobre la factura y se obtiene el valor que le corresponda.
                    Luego se debe agregar al output r.
                    """
                    raise NotImplemented

        return r[ids] if isinstance(ids, int) else r

    def compute_all(self, cr, uid, ids, line_filter=lambda line: True, tax_filter=lambda tax: True, context=None):
        # TODO reemplazar esta funcion, tal vez directamente la podemos no usar, esta para las lineas de aca abajo
                # 'ImpOpEx': inv.compute_all(line_filter=lambda line: len(line.invoice_line_tax_id) == 0)['amount_total'],
                # 'ImpIVA': inv.compute_all(tax_filter=lambda tax: 'IVA' in _get_parents(tax.tax_code_id))['amount_tax'],
                # 'ImpTrib': inv.compute_all(tax_filter=lambda tax: 'IVA' not in _get_parents(tax.tax_code_id))['amount_tax'],

        res = {}
        for inv in self.browse(cr, uid, ids, context=context):
            amounts = []
            for line in inv.invoice_line:
                if line_filter(line):
                    amounts.append(line.compute_all(tax_filter=tax_filter, context=context))

            s = {
                 'amount_total': 0,
                 'amount_tax': 0,
                 'amount_untaxed': 0,
                 'taxes': [],
                }
            for amount in amounts:
                for key, value in amount.items():
                    s[key] = s.get(key, 0) + value

            res[inv.id] = s

        return res.get(len(ids)==1 and ids[0], res)

    @api.multi
    def action_number(self):
        print 'self.number', self.reference
        # self.action_retrieve_cae()
        return super(invoice, self).action_number()

    def action_retrieve_cae(self, cr, uid, ids, context=None):
        """
        Contact to the AFIP to get a CAE number.
        """
        if context is None:
            context = {}

        conn_obj = self.pool.get('wsafip.connection')
        serv_obj = self.pool.get('wsafip.server')
        currency_obj = self.pool.get('res.currency')

        Servers = {}
        Requests = {}
        Inv2id = {}
        for inv in self.browse(cr, uid, ids, context=context):
            journal = inv.journal_id
            document_class = inv.journal_document_class_id.afip_document_class_id
            conn = inv.journal_document_class_id.afip_connection_id

            # Ignore journals with cae
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
            # Could not work if your number have not 8 digits.
            invoice_number = int(re_number.search(inv.reference).group())
            # invoice_number = int(re_number.search(inv.number).group())

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
                'ImpOpEx': inv.compute_all(line_filter=lambda line: len(line.invoice_line_tax_id) == 0)['amount_total'],
                'ImpIVA': inv.compute_all(tax_filter=lambda tax: 'IVA' in _get_parents(tax.tax_code_id))['amount_tax'],
                'ImpTrib': inv.compute_all(tax_filter=lambda tax: 'IVA' not in _get_parents(tax.tax_code_id))['amount_tax'],
                'FchServDesde': _f_date(inv.afip_service_start) if inv.afip_concept != '1' else None,
                'FchServHasta': _f_date(inv.afip_service_end) if inv.afip_concept != '1' else None,
                'FchVtoPago': _f_date(inv.date_due) if inv.afip_concept != '1' else None,
                'MonId': inv.currency_id.afip_code,
                'MonCotiz': currency_obj.compute(cr, uid, inv.currency_id.id, inv.company_id.currency_id.id, 1.),
                'CbtesAsoc': {'CbteAsoc': self.get_related_invoices(cr, uid, inv.id)},
                'Tributos': {'Tributo': self.get_taxes(cr, uid, inv.id)},
                'Iva': {'AlicIva': self.get_vat(cr, uid, inv.id)},
                'Opcionales': {'Opcional': self.get_optionals(cr, uid, inv.id)},
            }.iteritems() if v is not None)
            Inv2id[invoice_number] = inv.id

        for c_id, req in Requests.iteritems():
            conn = conn_obj.browse(cr, uid, c_id)
            res = serv_obj.wsfe_get_cae(
                cr, uid, [conn.server_id.id], c_id, req)
            for k, v in res.iteritems():
                if 'CAE' in v:
                    self.write(cr, uid, Inv2id[k], {
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

# TODO verificar esta
    # def invoice_print(self, cr, uid, ids, context=None):
    #     '''
    #     This function prints the invoice and mark it as sent, so that we can see more easily the next step of the workflow
    #     '''
    #     assert len(
    #         ids) == 1, 'This option should only be used for a single id at a time.'
    #     self.write(cr, uid, ids, {'sent': True}, context=context)
    #     datas = {
    #         'ids': ids,
    #         'model': 'account.invoice',
    #         'form': self.read(cr, uid, ids[0], context=context)
    #     }
    #     is_electronic = bool(
    #         self.browse(cr, uid, ids[0]).journal_id.afip_connection_id)
    #     return {
    #         'type': 'ir.actions.report.xml',
    #         'report_name': 'account.invoice_fe' if is_electronic else 'account.invoice',
    #         'datas': datas,
    #         'nodestroy': True
    #     }

    def afip_get_currency_code(self, cr, uid, ids, currency_id, context=None):
        """
        Take the AFIP currency code. If not set update database.
        """
        currency_obj = self.pool.get('res.currency')

        afip_code = currency_obj.read(
            cr, uid, currency_id, ['afip_code'], context=context)

        if not afip_code['afip_code']:
            self.afip_update_currency(cr, uid, ids, context=context)

            afip_code = currency_obj.read(
                cr, uid, currency_id, ['afip_code'], context=context)

        return afip_code['afip_code']

    def afip_update_currency(self, cr, uid, ids, context=None):
        """
        Update currency codes from AFIP database.
        """
        for inv in self.browse(cr, uid, ids[:1], context=context):
            auth = inv.afip_document_class_id.afip_connection_id

            # Only process if set to connect to afip
            if not auth:
                continue

            # Ignore invoice if connection server is not type WSFE.
            if auth.server_id.code != 'wsfe':
                continue

            auth.login()  # Login if nescesary.

            # Ignore if cant connect to server.
            if auth.state not in ['connected', 'clockshifted']:
                continue

            # Build request
            request = FEParamGetTiposMonedasSoapIn()
            request = auth.set_auth_request(request)

            response = get_bind(auth.server_id).FEParamGetTiposMonedas(request)

        pass

    def onchange_invoice_line(self, cr, uid, ids, invoice_line):
        product_obj = self.pool.get('product.product')
        invoice_line_obj = self.pool.get('account.invoice.line')
        res = {}

        product_types = set()

        # Existing lines.
        lines = {pid: d for a, pid, d in invoice_line if a in [1, 4]}
        for l in invoice_line_obj.browse(cr, uid, lines.keys()):
            if lines[l.id] and 'product_id' in lines[l.id]:
                # Change product_id
                product_types.update(
                    [p.type for p in product_obj.browse(cr, uid, [lines[l.id]['product_id']])])
            else:
                # No change product_id
                product_types.add(l.product_id.type)

        # Inserted new lines
        lines = [d for a, pid, d in invoice_line if a in [0]]
        for d in lines:
            if d and 'product_id' in d:
                product_types.update(
                    [p.type for p in product_obj.browse(cr, uid, [d['product_id']])])

        if product_types:
            res['value'] = {'afip_concept': _calc_concept(product_types)}

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
