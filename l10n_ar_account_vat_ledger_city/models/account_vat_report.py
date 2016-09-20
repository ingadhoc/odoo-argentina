# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import base64
import logging
_logger = logging.getLogger(__name__)


class account_vat_ledger(models.Model):
    _inherit = "account.vat.ledger"

    REGINFO_CV_ALICUOTAS = fields.Text(
        'REGINFO_CV_ALICUOTAS',
        readonly=True,
        )
    REGINFO_CV_COMPRAS_IMPORTACIONES = fields.Text(
        'REGINFO_CV_COMPRAS_IMPORTACIONES',
        readonly=True,
        )
    REGINFO_CV_CBTE = fields.Text(
        'REGINFO_CV_CBTE',
        readonly=True,
        )
    REGINFO_CV_CABECERA = fields.Text(
        'REGINFO_CV_CABECERA',
        readonly=True,
        )
    vouchers_file = fields.Binary(
        _('Vouchers File'),
        compute='get_files',
        readonly=True
        )
    vouchers_filename = fields.Char(
        _('Vouchers Filename'),
        readonly=True,
        compute='get_files',
        )
    aliquots_file = fields.Binary(
        _('Aliquots File'),
        compute='get_files',
        readonly=True
        )
    aliquots_filename = fields.Char(
        _('Aliquots Filename'),
        readonly=True,
        compute='get_files',
        )
    import_aliquots_file = fields.Binary(
        _('Import Aliquots File'),
        compute='get_files',
        readonly=True
        )
    import_aliquots_filename = fields.Char(
        _('Import Aliquots Filename'),
        readonly=True,
        compute='get_files',
        )
    prorate_tax_credit = fields.Boolean(
        'Prorate Tax Credit',
        )
    prorate_type = fields.Selection(
        [('global', 'Global'), ('by_voucher', 'By Voucher')],
        'Prorate Type',
        )
    tax_credit_computable_amount = fields.Float(
        'Credit Computable Amount',
        )
    sequence = fields.Integer(
        'Sequence',
        default=0,
        required=True,
        help='Se deberá indicar si la presentación es Original (00) o '
        'Rectificativa y su orden'
        )

    @api.model
    def format_amount(self, amount, padding=15, decimals=2, invoice=False):
        # get amounts on correct sign despite conifiguration on taxes and tax
        # codes
        # TODO remove this and perhups invoice argument (we always send invoice)
        # for invoice refund we dont change sign (we do this before)
        # if invoice:
        #     amount = abs(amount)
        #     if invoice.type in ['in_refund', 'out_refund']:
        #         amount = -1.0 * amount
        # if amount < 0:
        #     template = "-{:0>%dd}" % (padding-1)
        # else:
        template = "{:0>%dd}" % (padding)
        return template.format(
            int(round(abs(amount) * 10**decimals, decimals)))

    @api.one
    @api.depends(
        'REGINFO_CV_CBTE', 'REGINFO_CV_ALICUOTAS', 'type', 'period_id.name')
    def get_files(self):
        if self.REGINFO_CV_ALICUOTAS:
            self.aliquots_filename = _('Alicuots_%s_%s.txt') % (
                self.type, self.period_id.name)
            self.aliquots_file = base64.encodestring(
                self.REGINFO_CV_ALICUOTAS.encode('utf-8'))
        if self.REGINFO_CV_COMPRAS_IMPORTACIONES:
            self.import_aliquots_filename = _('Import_Alicuots_%s_%s.txt') % (
                self.type, self.period_id.name)
            self.import_aliquots_file = base64.encodestring(
                self.REGINFO_CV_COMPRAS_IMPORTACIONES.encode('utf-8'))
        if self.REGINFO_CV_CBTE:
            self.vouchers_filename = _('Vouchers_%s_%s.txt') % (
                self.type, self.period_id.name)
            self.vouchers_file = base64.encodestring(
                self.REGINFO_CV_CBTE.encode('utf-8'))

    @api.one
    def compute_citi_data(self):
        # no lo estamos usando
        # self.get_REGINFO_CV_CABECERA()
        self.get_REGINFO_CV_CBTE()
        self.get_REGINFO_CV_ALICUOTAS()
        if self.type == 'purchase':
            self.get_REGINFO_CV_COMPRAS_IMPORTACIONES()

    @api.model
    def get_partner_document_code(self, partner):
        # TODO agregar validaciones para los que se presentan sin numero de
        # documento para operaciones menores a 1000 segun doc especificacion
        # regimen de...
        if partner.document_type_id.afip_code:
            return "{:0>2d}".format(partner.document_type_id.afip_code)
        else:
            return '99'

    @api.model
    def get_partner_document_number(self, partner):
        # TODO agregar validaciones para los que se presentan sin numero de
        # documento para operaciones menores a 1000 segun doc especificacion
        # regimen de...
        return (partner.document_number or '').rjust(20, '0')

    @api.model
    def get_point_of_sale(self, invoice):
        return "{:0>5d}".format(invoice.point_of_sale)

    # @api.one
    # def get_REGINFO_CV_CABECERA(self):
    #     res = []

    #     # Campo 1: CUIT Informante.
    #     if not self.company_id.partner_id.vat:
    #         raise Warning(_('No vat configured for company %s') % (
    #             self.company_id.name))
    #     res.append(self.company_id.partner_id.vat[2:])

    #     # Campo 2: Período
    #     res.append(fields.Date.from_string(
    #         self.period_id.date_start).strftime('%Y%m'))

    #     # Campo 3: Secuencia
    #     res.append("-{:0>2d}".format(self.sequence))

    #     # Campo 4: Sin Movimiento
    #     if self.invoice_ids:
    #         res.append('S')
    #     else:
    #         res.append('N')

    #     res += self.get_proratate_data()
    #     # Campo 11: Crédito Fiscal Contrib. Seg. Soc. y Otros Conceptos
    #     # Campo 12: Crédito Fiscal Computable Contrib. Seg. Soc. y Otros Conceptos.
    #     self.REGINFO_CV_CABECERA = ''.join(res)

    # @api.multi
    # def get_proratate_data(self):
    #     """
    #     # Campo 5: Prorratear Crédito Fiscal Computable
    #     # Campo 6: Crédito Fiscal Computable Global ó Por Comprobante
    #     # Campo 7: Importe Crédito Fiscal Computable Global
    #     # Campo 8: Importe Crédito Fiscal Computable, con asignación directa
    #     # Campo 9: Importe Crédito Fiscal Computable, determinado por prorrateo
    #     # Campo 10: Importe Crédito Fiscal no Computable Global.
    #     """
    #     self.ensure_one()
    #     res = []
    #     if self.prorate_tax_credit:
    #         res.append('S')
    #         if self.prorate_type == 'global':
    #             res += [
    #                 '1',
    #                 self.format_amount(self.tax_credit_computable_amount),
    #                 self.format_amount(self.tax_credit_computable_amount),
    #                 ]
    #         else:
    #             res += [
    #                 '2',
    #                 self.format_amount(0),
    #                 self.format_amount(0),
    #                 ]
    #     else:
    #         res += [
    #             'N',
    #             '0',
    #             self.format_amount(0),
    #             self.format_amount(0),
    #             ]
    #     return res

    @api.multi
    def get_citi_invoices(self):
        self.ensure_one()
        return self.env['account.invoice'].search([
            ('afip_document_class_id.export_to_citi', '=', True),
            ('id', 'in', self.invoice_ids.ids)])

    @api.one
    def get_REGINFO_CV_CBTE(self):
        res = []
        invoices = self.get_citi_invoices()
        invoices.check_argentinian_invoice_taxes()
        if self.type == 'purchase':
            partners = invoices.mapped('commercial_partner_id').filtered(
                lambda r: r.document_type_id.afip_code in (False, 99) or not r.document_number)
            if partners:
                raise Warning(_("On purchase citi, partner document is mandatory and partner document type must be different from 99. Partners %s") % partners.ids)

        for inv in invoices:
            # only vat taxes with codes 3, 4, 5, 6, 8, 9
            # segun: http://contadoresenred.com/regimen-de-informacion-de-
            # compras-y-ventas-rg-3685-como-cargar-la-informacion/
            # empezamos a contar los codigos 1 (no gravado) y 2 (exento)
            # si no hay alicuotas, sumamos una de esta con 0, 0, 0 en detalle
            # usamos mapped por si hay afip codes duplicados (ej. manual y auto)
            cant_alicuotas = len(inv.vat_tax_ids.filtered(
                lambda r: r.tax_code_id.afip_code in [3, 4, 5, 6, 8, 9]
            ).mapped('tax_code_id.afip_code'))
            if not cant_alicuotas and inv.vat_tax_ids.filtered(
                    lambda r: r.tax_code_id.afip_code in [1, 2]):
                cant_alicuotas = 1

            row = [
                # Campo 1: Fecha de comprobante
                fields.Date.from_string(inv.date_invoice).strftime('%Y%m%d'),

                # Campo 2: Tipo de Comprobante.
                "{:0>3d}".format(inv.afip_document_class_id.afip_code),

                # Campo 3: Punto de Venta
                self.get_point_of_sale(inv),

                # Campo 4: Número de Comprobante
                # TODO agregar estos casos de uso
                # Si se trata de un comprobante de varias hojas, se deberá informar el número de documento de la primera hoja, teniendo en cuenta lo normado en el  artículo 23, inciso a), punto 6., de la Resolución General N° 1.415, sus modificatorias y complementarias.
                # En el supuesto de registrar de manera agrupada por totales diarios, se deberá consignar el primer número de comprobante del rango a considerar.
                "{:0>20d}".format(inv.invoice_number)
                ]

            if self.type == 'sale':
                # Campo 5: Número de Comprobante Hasta.
                # TODO agregar esto En el resto de los casos se consignará el dato registrado en el campo 4
                row.append("{:0>20d}".format(inv.invoice_number))
            else:
                # Campo 5: Despacho de importación
                if inv.afip_document_class_id.afip_code == 66:
                    row.append((inv.afip_document_number or inv.number or '').rjust(
                        16, '0'))
                else:
                    row.append(''.rjust(16, ' '))

            row += [
                # Campo 6: Código de documento del comprador. 
                self.get_partner_document_code(inv.commercial_partner_id),

                # Campo 7: Número de Identificación del comprador
                self.get_partner_document_number(inv.commercial_partner_id),

                # Campo 8: Apellido y Nombre del comprador.
                inv.commercial_partner_id.name.encode(
                    'ascii', 'ignore').ljust(30, ' ')[:30],

                # Campo 9: Importe Total de la Operación.
                self.format_amount(inv.amount_total, invoice=inv),

                # Campo 10: Importe total de conceptos que no integran el precio neto gravado
                self.format_amount(inv.vat_untaxed, invoice=inv),
                ]

            if self.type == 'sale':
                row += [
                    # Campo 11: Percepción a no categorizados
                    self.format_amount(
                        sum(inv.tax_line.filtered(
                            lambda r: r.tax_code_id.type == 'perception' and r.tax_code_id.tax == 'vat' and r.tax_code_id.application == 'national_taxes').mapped(
                            'tax_amount')), invoice=inv),

                    # Campo 12: Importe de operaciones exentas
                    self.format_amount(inv.vat_exempt_amount, invoice=inv),
                    ]
            else:
                row += [
                    # Campo 11: Importe de operaciones exentas
                    self.format_amount(inv.vat_exempt_amount, invoice=inv),

                    # Campo 12: Importe de percepciones o pagos a cuenta del Impuesto al Valor Agregado
                    self.format_amount(
                        sum(inv.tax_line.filtered(
                            lambda r: r.tax_code_id.type == 'perception' and r.tax_code_id.tax == 'vat' and r.tax_code_id.application == 'national_taxes').mapped(
                            'tax_amount')), invoice=inv),
                    ]

            row += [
                # Campo 13: Importe de percepciones o pagos a cuenta de impuestos nacionales
                self.format_amount(
                    sum(inv.tax_line.filtered(
                        lambda r: r.tax_code_id.type == 'perception' and r.tax_code_id.tax != 'vat' and r.tax_code_id.application == 'national_taxes').mapped(
                        'tax_amount')), invoice=inv),

                # Campo 14: Importe de percepciones de ingresos brutos
                self.format_amount(
                    sum(inv.tax_line.filtered(
                        lambda r: r.tax_code_id.type == 'perception' and r.tax_code_id.application == 'provincial_taxes').mapped(
                        'tax_amount')), invoice=inv),

                # Campo 15: Importe de percepciones de impuestos municipales
                self.format_amount(
                    sum(inv.tax_line.filtered(
                        lambda r: r.tax_code_id.type == 'perception' and r.tax_code_id.application == 'municipal_taxes').mapped(
                        'tax_amount')), invoice=inv),

                # Campo 16: Importe de impuestos internos
                self.format_amount(
                    sum(inv.tax_line.filtered(
                        lambda r: r.tax_code_id.application == 'internal_taxes').mapped(
                        'tax_amount')), invoice=inv),

                # Campo 17: Código de Moneda
                str(inv.currency_id.afip_code),

                # Campo 18: Tipo de Cambio
                self.format_amount(
                    inv.currency_rate or inv.currency_id.with_context(
                        date=inv.date_invoice).compute(
                            1., inv.company_id.currency_id),
                    padding=10, decimals=6),

                # Campo 19: Cantidad de alícuotas de IVA
                str(cant_alicuotas),

                # Campo 20: Código de operación.
                # WARNING. segun la plantilla es 0 si no es ninguna
                # TODO ver que no se informe un codigo si no correpsonde,
                # tal vez da error
                inv.fiscal_position.afip_code or ' ',
                ]

            if self.type == 'sale':
                row += [
                    # Campo 21: Otros Tributos
                    self.format_amount(
                        sum(inv.tax_line.filtered(
                            lambda r: r.tax_code_id.application == 'others').mapped(
                            'tax_amount')), invoice=inv),

                    # Campo 22: vencimiento comprobante (no figura en instructivo pero si en aplicativo)
                    # para tique no se informa
                    (inv.afip_document_class_id.afip_code in [81, 82, 83] and
                        '00000000' or
                        fields.Date.from_string(inv.date_due).strftime(
                            '%Y%m%d')),
                    ]
            else:
                # Campo 21: Crédito Fiscal Computable
                if self.prorate_tax_credit:
                    if self.prorate_type == 'global':
                        row.append(self.format_amount(0), invoice=inv)
                    else:
                        # row.append(self.format_amount(0))
                        raise Warning(_('by_voucher not implemented yet'))
                else:
                    row.append(self.format_amount(inv.vat_amount, invoice=inv))

                row += [
                    # Campo 22: Otros Tributos
                    self.format_amount(
                        sum(inv.tax_line.filtered(
                            lambda r: r.tax_code_id.application == 'others').mapped(
                            'tax_amount')), invoice=inv),

                    # TODO implementar estos 3
                    # Campo 23: CUIT Emisor / Corredor
                    # Se informará sólo si en el campo "Tipo de Comprobante" se consigna '033', '058', '059', '060' ó '063'. Si para éstos comprobantes no interviene un tercero en la operación, se consignará la C.U.I.T. del informante. Para el resto de los comprobantes se completará con ceros
                    self.format_amount(0, padding=11, invoice=inv),

                    # Campo 24: Denominación Emisor / Corredor
                    ''.ljust(30, ' ')[:30],

                    # Campo 25: IVA Comisión
                    # Si el campo 23 es distinto de cero se consignará el importe del I.V.A. de la comisión
                    self.format_amount(0, invoice=inv),
                    ]
            res.append(''.join(row))
        self.REGINFO_CV_CBTE = '\r\n'.join(res)

    @api.multi
    def get_tax_row(self, invoice, base_amount, code, tax_amount):
        self.ensure_one()
        inv = invoice
        row = [
            # Campo 1: Tipo de Comprobante
            "{:0>3d}".format(inv.afip_document_class_id.afip_code),

            # Campo 2: Punto de Venta
            self.get_point_of_sale(inv),

            # Campo 3: Número de Comprobante
            "{:0>20d}".format(inv.invoice_number),
            ]
        if self.type == 'sale':
            row += [
                # Campo 4: Importe Neto Gravado
                self.format_amount(base_amount, invoice=inv),

                # Campo 5: Alícuota de IVA.
                str(code).rjust(4, '0'),

                # Campo 6: Impuesto Liquidado.
                self.format_amount(tax_amount, invoice=inv),
            ]
        else:
            row += [
                # Campo 4: Código de documento del vendedor
                self.get_partner_document_code(
                    inv.commercial_partner_id),

                # Campo 5: Número de identificación del vendedor
                self.get_partner_document_number(
                    inv.commercial_partner_id),

                # Campo 6: Importe Neto Gravado
                self.format_amount(base_amount, invoice=inv),

                # Campo 7: Alícuota de IVA.
                str(code).rjust(4, '0'),

                # Campo 8: Impuesto Liquidado.
                self.format_amount(tax_amount, invoice=inv),
            ]
        return row

    @api.one
    def get_REGINFO_CV_ALICUOTAS(self):
        res = []
        for inv in self.get_citi_invoices().filtered(
                lambda r: r.afip_document_class_id.afip_code != 66):
            vat_taxes = inv.vat_tax_ids.filtered(
                    lambda r: r.tax_code_id.afip_code in [3, 4, 5, 6, 8, 9])

            # if only exempt or no gravado, we add one line with 0, 0, 0
            if not vat_taxes and inv.vat_tax_ids.filtered(
                    lambda r: r.tax_code_id.afip_code in [1, 2]):
                res.append(''.join(self.get_tax_row(inv, 0.0, 3, 0.0)))

            # we group by afip_code
            for afip_code in vat_taxes.mapped('tax_code_id.afip_code'):
                taxes = vat_taxes.filtered(
                    lambda x: x.tax_code_id.afip_code == afip_code)
                res.append(''.join(self.get_tax_row(
                    inv,
                    sum(taxes.mapped('base_amount')),
                    afip_code,
                    sum(taxes.mapped('tax_amount')),
                    )))
        self.REGINFO_CV_ALICUOTAS = '\r\n'.join(res)

    @api.one
    def get_REGINFO_CV_COMPRAS_IMPORTACIONES(self):
        res = []
        for inv in self.get_citi_invoices().filtered(
                lambda r: r.afip_document_class_id.afip_code == 66):
            vat_taxes = inv.vat_tax_ids.filtered(
                lambda r: r.tax_code_id.afip_code in [3, 4, 5, 6, 8, 9])

            # we group by afip_code
            for afip_code in vat_taxes.mapped('tax_code_id.afip_code'):
                taxes = vat_taxes.filtered(
                    lambda x: x.tax_code_id.afip_code == afip_code)
                base_amount = sum(taxes.mapped('base_amount'))
                tax_amount = sum(taxes.mapped('tax_amount'))
                row = [
                    # Campo 1: Despacho de importación.
                    (inv.afip_document_number or inv.number or '').rjust(
                        16, '0'),

                    # Campo 2: Importe Neto Gravado
                    self.format_amount(base_amount, invoice=inv),

                    # Campo 3: Alícuota de IVA
                    str(afip_code).rjust(4, '0'),

                    # Campo 4: Impuesto Liquidado.
                    self.format_amount(tax_amount, invoice=inv),
                    ]
                res.append(''.join(row))
        self.REGINFO_CV_COMPRAS_IMPORTACIONES = '\r\n'.join(res)
