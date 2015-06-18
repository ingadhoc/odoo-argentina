# -*- coding: utf-8 -*-
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
    REGINFO_CV_CBTE = fields.Text(
        'REGINFO_CV_CBTE',
        readonly=True,
        )
    REGINFO_CV_CABECERA = fields.Text(
        'REGINFO_CV_CABECERA',
        readonly=True,
        )
    vouchers_file = fields.Binary(
        'Vouchers File',
        compute='get_files',
        readonly=True
        )
    vouchers_filename = fields.Char(
        'Vouchers Filename',
        readonly=True,
        compute='get_files',
        )
    aliquots_file = fields.Binary(
        'Aliquots File',
        compute='get_files',
        readonly=True
        )
    aliquots_filename = fields.Char(
        'Aliquots Filename',
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
        help='Se deberá indicar si la presentación es Original (00) o Rectificativa y su orden'
        )

    _sql_constraints = [('number_unique', 'unique(number, company_id)',
                         'Number Must be Unique per Company!')]

    @api.model
    def format_amount(self, amount, padding=15, decimals=2):
        if amount < 0:
            template = "-{:0>%dd}" % (padding-1)
        else:
            template = "{:0>%dd}" % (padding)
        return template.format(
            int(round(amount, decimals) * 10**decimals))

    @api.one
    @api.depends(
        'REGINFO_CV_CBTE', 'REGINFO_CV_ALICUOTAS', 'type', 'period_id.name')
    def get_files(self):
        if self.REGINFO_CV_ALICUOTAS:
            self.aliquots_filename = _('Alicuots_%s_%s.txt') % (
                self.type, self.period_id.name)
            self.aliquots_file = base64.encodestring(
                self.REGINFO_CV_ALICUOTAS.encode('utf-8'))
        if self.REGINFO_CV_CBTE:
            self.vouchers_filename = _('Vouchers_%s_%s.txt') % (
                self.type, self.period_id.name)
            self.vouchers_file = base64.encodestring(
                self.REGINFO_CV_CBTE.encode('utf-8'))

    @api.one
    def compute_citi_data(self):
        self.get_REGINFO_CV_CABECERA()
        self.get_REGINFO_CV_CBTE()
        self.get_REGINFO_CV_ALICUOTAS()

    @api.model
    def get_partner_document_code(self, partner):
        if partner.document_type_id.afip_code:
            return "{:0>2d}".format(partner.document_type_id.afip_code)
        else:
        # TODO agregar validaciones para los que se presentan sin numero de documento para operaciones menores a 1000 segun doc especificacion regimen de...
            return '99'

    @api.model
    def get_partner_document_number(self, partner):
        # TODO agregar validaciones para los que se presentan sin numero de documento para operaciones menores a 1000 segun doc especificacion regimen de...
        return (partner.document_number or '').rjust(20, '0')

    @api.model
    def get_point_of_sale(self, invoice):
        if invoice.afip_document_class_id.afip_code in [033, 99, 331, 332]:
            point_of_sale = 0
        else:
            point_of_sale = invoice.point_of_sale
        return "{:0>5d}".format(point_of_sale)

    @api.one
    def get_REGINFO_CV_CABECERA(self):
        res = []

        # Campo 1: CUIT Informante.
        if not self.company_id.partner_id.vat:
            raise Warning(_('No vat configured for company %s') % (
                self.company_id.name))
        res.append(self.company_id.partner_id.vat[2:])

        # Campo 2: Período
        res.append(fields.Date.from_string(
            self.period_id.date_start).strftime('%Y%m'))

        # Campo 3: Secuencia
        res.append("-{:0>2d}".format(self.sequence))

        # Campo 4: Sin Movimiento
        if self.invoice_ids:
            res.append('S')
        else:
            res.append('N')

        res += self.get_proratate_data()
        # Campo 11: Crédito Fiscal Contrib. Seg. Soc. y Otros Conceptos
        # Campo 12: Crédito Fiscal Computable Contrib. Seg. Soc. y Otros Conceptos.
        self.REGINFO_CV_CABECERA = ''.join(res)

    @api.multi
    def get_proratate_data(self):
        """
        # Campo 5: Prorratear Crédito Fiscal Computable
        # Campo 6: Crédito Fiscal Computable Global ó Por Comprobante
        # Campo 7: Importe Crédito Fiscal Computable Global
        # Campo 8: Importe Crédito Fiscal Computable, con asignación directa
        # Campo 9: Importe Crédito Fiscal Computable, determinado por prorrateo
        # Campo 10: Importe Crédito Fiscal no Computable Global.
        """
        self.ensure_one()
        res = []
        if self.prorate_tax_credit:
            res.append('S')
            if self.prorate_type == 'global':
                res += [
                    '1',
                    self.format_amount(self.tax_credit_computable_amount),
                    self.format_amount(self.tax_credit_computable_amount),
                    ]
            else:
                res += [
                    '2',
                    self.format_amount(0),
                    self.format_amount(0),
                    ]
        else:
            res += [
                'N',
                '0',
                self.format_amount(0),
                self.format_amount(0),
                ]
        return res

    @api.one
    def get_REGINFO_CV_CBTE(self):
        res = []
        self.invoice_ids.check_argentinian_invoice_taxes()
        if self.type == 'purchase':
            partners = self.invoice_ids.mapped('commercial_partner_id').filtered(
                lambda r: r.document_type_id.afip_code in (False, 99) or not r.document_number)
            if partners:
                raise Warning(_("On purchase citi, partner document is mandatory and partner document type must be different from 99. Partners %s") % partners.ids)

        for inv in self.invoice_ids:
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
                # Para los comprobantes correspondientes a los códigos '033', '331' y '332' el presente campo deberá completarse con el "Código de Operación Electrónica    -COE-".
                # En el supuesto de registrar de manera agrupada por totales diarios, se deberá consignar el primer número de comprobante del rango a considerar.
                "{:0>20d}".format(inv.invoice_number)
                ]

            if self.type == 'sale':
                # Campo 5: Número de Comprobante Hasta.
                # TODO agregar esto En el resto de los casos se consignará el dato registrado en el campo 4
                row.append("{:0>20d}".format(inv.invoice_number))
            else:
                # Campo 5: Despacho de importación
                # TODO agregar despacho de importacion en algun lugar
                row.append(str('').rjust(16, ' '))

            row += [
                # Campo 6: Código de documento del comprador. 
                self.get_partner_document_code(inv.commercial_partner_id),

                # Campo 7: Número de Identificación del comprador
                self.get_partner_document_number(inv.commercial_partner_id),

                # Campo 8: Apellido y Nombre del comprador.
                inv.commercial_partner_id.name.encode(
                    'ascii', 'ignore').ljust(30, ' ')[:30],

                # Campo 9: Importe Total de la Operación.
                self.format_amount(inv.amount_total),

                # Campo 10: Importe total de conceptos que no integran el precio neto gravado
                # TODO implementar
                self.format_amount(0),
                ]

            if self.type == 'sale':
                row += [
                    # Campo 11: Percepción a no categorizados
                    # TODO implementar
                    self.format_amount(0),

                    # Campo 12: Importe de operaciones exentas
                    self.format_amount(inv.exempt_amount),
                    ]
            else:
                row += [
                    # Campo 11: Importe de operaciones exentas
                    self.format_amount(inv.exempt_amount),

                    # Campo 12: Importe de percepciones o pagos a cuenta del Impuesto al Valor Agregado
                    self.format_amount(
                        sum(inv.tax_line.filtered(
                            lambda r: r.tax_code_id.type == 'perception' and r.tax_code_id.tax == 'vat' and r.tax_code_id.application == 'national_taxes').mapped(
                            'tax_amount'))),
                    ]

            row += [
                # Campo 13: Importe de percepciones o pagos a cuenta de impuestos nacionales
                self.format_amount(
                    sum(inv.tax_line.filtered(
                        lambda r: r.tax_code_id.type == 'perception' and r.tax_code_id.tax != 'vat' and r.tax_code_id.application == 'national_taxes').mapped(
                        'tax_amount'))),

                # Campo 14: Importe de percepciones de ingresos brutos
                self.format_amount(
                    sum(inv.tax_line.filtered(
                        lambda r: r.tax_code_id.type == 'perception' and r.tax_code_id.application == 'provincial_taxes').mapped(
                        'tax_amount'))),

                # Campo 15: Importe de percepciones de impuestos municipales
                self.format_amount(
                    sum(inv.tax_line.filtered(
                        lambda r: r.tax_code_id.type == 'perception' and r.tax_code_id.application == 'municipal_taxes').mapped(
                        'tax_amount'))),

                # Campo 16: Importe de impuestos internos
                self.format_amount(
                    sum(inv.tax_line.filtered(
                        lambda r: r.tax_code_id.application == 'internal_taxes').mapped(
                        'tax_amount'))),

                # Campo 17: Código de Moneda
                str(inv.currency_id.afip_code),

                # Campo 18: Tipo de Cambio
                self.format_amount(
                    inv.currency_id.with_context(
                        date=inv.date_invoice).compute(
                            1., inv.company_id.currency_id),
                    padding=10, decimals=6),

                # Campo 19: Cantidad de alícuotas de IVA
                str(len(inv.vat_tax_ids)),

                # Campo 20: Código de operación.
                # WARNING. segun la plantilla es 0 si no es ninguna
                inv.exempt_amount and inv.fiscal_position.afip_code or ' ',
                ]

            if self.type == 'sale':
                row += [
                    # Campo 21: Otros Tributos
                    self.format_amount(
                        sum(inv.tax_line.filtered(
                            lambda r: r.tax_code_id.application == 'others').mapped(
                            'tax_amount'))),

                    # Campo 22: vencimiento comprobante (no figura en instructivo pero si en aplicativo)
                    fields.Date.from_string(inv.date_due).strftime('%Y%m%d'),
                    ]
            else:
                # Campo 21: Crédito Fiscal Computable
                if self.prorate_tax_credit:
                    if self.prorate_type == 'global':
                        row.append(self.format_amount(0))
                    else:
                        # row.append(self.format_amount(0))
                        raise Warning(_('by_voucher not implemented yet'))
                else:
                    row.append(self.format_amount(inv.vat_amount))

                row += [
                    # Campo 22: Otros Tributos
                    self.format_amount(
                        sum(inv.tax_line.filtered(
                            lambda r: r.tax_code_id.application == 'others').mapped(
                            'tax_amount'))),

                    # TODO implementar estos 3
                    # Campo 23: CUIT Emisor / Corredor
                    # Se informará sólo si en el campo "Tipo de Comprobante" se consigna '033', '058', '059', '060' ó '063'. Si para éstos comprobantes no interviene un tercero en la operación, se consignará la C.U.I.T. del informante. Para el resto de los comprobantes se completará con ceros
                    self.format_amount(0, padding=11),

                    # Campo 24: Denominación Emisor / Corredor
                    ''.ljust(30, ' ')[:30],

                    # Campo 25: IVA Comisión
                    # Si el campo 23 es distinto de cero se consignará el importe del I.V.A. de la comisión
                    self.format_amount(0),
                    ]
            res.append(''.join(row))
        self.REGINFO_CV_CBTE = '\r\n'.join(res)

    @api.one
    def get_REGINFO_CV_ALICUOTAS(self):
        res = []
        for inv in self.invoice_ids:
            for tax in inv.vat_tax_ids:
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
                        self.format_amount(tax.base_amount),

                        # Campo 5: Alícuota de IVA.
                        str(tax.tax_code_id.afip_code).rjust(4, '0'),

                        # Campo 6: Impuesto Liquidado.
                        self.format_amount(tax.tax_amount),
                    ]
                else:
                    row += [
                        # Campo 4: Código de documento del vendedor
                        self.get_partner_document_code(inv.commercial_partner_id),

                        # Campo 5: Número de identificación del vendedor
                        self.get_partner_document_number(inv.commercial_partner_id),

                        # Campo 6: Importe Neto Gravado
                        self.format_amount(tax.base_amount),

                        # Campo 7: Alícuota de IVA.
                        str(tax.tax_code_id.afip_code).rjust(4, '0'),

                        # Campo 8: Impuesto Liquidado.
                        self.format_amount(tax.tax_amount),
                    ]
                res.append(''.join(row))
        self.REGINFO_CV_ALICUOTAS = '\r\n'.join(res)
