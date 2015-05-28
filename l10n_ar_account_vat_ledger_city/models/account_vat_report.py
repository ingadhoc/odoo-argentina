# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import base64
import logging
_logger = logging.getLogger(__name__)


class account_vat_ledger(models.Model):
    _inherit = "account.vat.ledger"

    report_content = fields.Text(
        'Report Content',
        compute='get_files',
        readonly=True
        )
    REGINFO_CV_ALICUOTAS = fields.Text(
        'REGINFO_CV_ALICUOTAS',
        compute='get_REGINFO_CV_ALICUOTAS',
        )
    REGINFO_CV_CBTE = fields.Text(
        'REGINFO_CV_CBTE',
        compute='get_REGINFO_CV_CBTE',
        )
    REGINFO_CV_CABECERA = fields.Text(
        'REGINFO_CV_CABECERA',
        compute='get_REGINFO_CV_CABECERA',
        )
    report = fields.Binary(
        'Download Report',
        compute='get_files',
        readonly=True
        )
    report_filename = fields.Char(
        'Filename',
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
                         'Number Must be Unique per Company!'), ]

    @api.model
    def format_amount(self, amount, padding=15, decimals=2):
        if amount < 0:
            template = "-{:0>%dd}" % (padding-1)
        else:
            template = "{:0>%dd}" % (padding)
        return template.format(
            int(round(amount, decimals) * 10**decimals))

    @api.one
    @api.depends('invoice_ids')
    def get_files(self):
        report_content = '123123'
        self.report_content = report_content
        if self.report_content:
            self.report_filename = 'request.txt'
            self.report = base64.encodestring(
                self.report_content)

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
    @api.depends('invoice_ids')
    def get_REGINFO_CV_CBTE(self):
        res = []
        for inv in self.invoice_ids:
            if inv.exempt_amount == 0:
                # TODO implementar de acuerdo a
                # Si la alícuota de IVA  es igual a cero (0) o la operación responde a una operación de Canje se deberá completar de acuerdo con la siguiente codificación:
                # Z- Exportaciones a la zona franca.
                # X- Exportaciones al exterior.
                # E- Operaciones exentas.
                # N- No gravado.
                # C- Operaciones de Canje.
                _logger.warning('Excempt operations not implemented yet')

            if inv.company_id.currency_id != inv.currency_id:
                # TODO implementar otras monedas
                _logger.warning('Other Currency different thatn company currency not implemented yet')
            # row = []
            # row.append(
            row = [
                # Campo 1: Fecha de comprobante
                fields.Date.from_string(inv.date_invoice).strftime('%Y%m%d'),

                # Campo 2: Tipo de Comprobante.
                "{:0>3d}".format(inv.afip_document_class_id.afip_code),

                # Campo 3: Punto de Venta
                # TODO implementar Para los comprobantes correspondientes a los códigos '033', '099', '331' y '332', el presente campo deberá completarse con ceros.
                "{:0>5d}".format(inv.point_of_sale),

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
                # TODO agregar validaciones para los que se presentan sin numero de documento para operaciones menores a 1000 segun doc especificacion regimen de...
                str(inv.commercial_partner_id.document_type_id.afip_code) or '99',

                # Campo 7: Número de Identificación del comprador
                str(inv.commercial_partner_id.document_number).rjust(20, '0'),

                # Campo 8: Apellido y Nombre del comprador.
                inv.commercial_partner_id.name.ljust(30, ' ')[:30],

                # Campo 9: Importe Total de la Operación.
                self.format_amount(inv.amount_total),

                # Campo 10: Importe total de conceptos que no integran el precio neto gravado
                self.format_amount(inv.amount_untaxed),
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
                    # TODo implementar
                    self.format_amount(0),
                    ]

            row += [
                # Campo 13: Importe de percepciones o pagos a cuenta de impuestos nacionales
                # TODO implementar
                self.format_amount(0),

                # Campo 14: Importe de percepciones de ingresos brutos
                # TODO implementar
                self.format_amount(0),

                # Campo 15: Importe de percepciones de impuestos municipales
                # TODO implementar
                self.format_amount(0),

                # Campo 16: Importe de impuestos internos
                # TODO implementar
                self.format_amount(0),

                # Campo 17: Código de Moneda
                str(inv.currency_id.afip_code),

                # Campo 18: Tipo de Cambio
                # TODO implementar otras monedas
                self.format_amount(1, padding=10, decimals=6),

                # Campo 19: Cantidad de alícuotas de IVA
                str(len(inv.get_vat()[0])),

                # Campo 20: Código de operación.
                # TODO implementar operacionex excentas
                # WARNING. segun la plantilla es 0 si no es ninguna
                ' ',
                ]

            if self.type == 'sale':
                row += [
                    # Campo 21: Otros Tributos
                    # TODO implementar
                    self.format_amount(0),

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
                    # TODO poner el total de IVA
                    row.append(self.format_amount(0))

                row += [
                    # Campo 22: Otros Tributos
                    # TODO implementar
                    self.format_amount(0),

                    # Campo 23: CUIT Emisor / Corredor
                    # TODO implementar
                    # Se informará sólo si en el campo "Tipo de Comprobante" se consigna '033', '058', '059', '060' ó '063'. Si para éstos comprobantes no interviene un tercero en la operación, se consignará la C.U.I.T. del informante. Para el resto de los comprobantes se completará con ceros
                    self.format_amount(0, padding=11),

                    # Campo 24: Denominación Emisor / Corredor
                    # TODO implementar
                    ''.ljust(30, ' ')[:30],

                    # Campo 25: IVA Comisión
                    # Si el campo 23 es distinto de cero se consignará el importe del I.V.A. de la comisión
                    self.format_amount(0),
                    ]
            res.append(''.join(row))
        self.REGINFO_CV_CBTE = '\n'.join(res)

    @api.one
    @api.depends('invoice_ids')
    def get_REGINFO_CV_ALICUOTAS(self):
        res = []
        for inv in self.invoice_ids:
            for tax in inv.get_vat()[0]:
                row = [
                    # Campo 1: Tipo de Comprobante
                    "{:0>3d}".format(inv.afip_document_class_id.afip_code),

                    # Campo 2: Punto de Venta
                    "{:0>5d}".format(inv.point_of_sale),

                    # Campo 3: Número de Comprobante
                    "{:0>20d}".format(inv.invoice_number),
                    ]

                if self.type == 'sale':
                    row += [
                        # Campo 4: Importe Neto Gravado
                        self.format_amount(tax['BaseImp']),

                        # Campo 5: Alícuota de IVA.
                        str(tax['Id']).rjust(4, '0'),

                        # Campo 6: Impuesto Liquidado.
                        self.format_amount(tax['Importe']),
                    ]
                else:
                    row += [
                        # Campo 4: Código de documento del vendedor
                        str(inv.commercial_partner_id.document_type_id.afip_code) or '99',

                        # Campo 5: Número de identificación del vendedor
                        str(inv.commercial_partner_id.document_number).rjust(20, '0'),

                        # Campo 6: Importe Neto Gravado
                        self.format_amount(tax['BaseImp']),

                        # Campo 7: Alícuota de IVA.
                        str(tax['Id']).rjust(4, '0'),

                        # Campo 8: Impuesto Liquidado.
                        self.format_amount(tax['Importe']),
                    ]
                res.append(''.join(row))
        self.REGINFO_CV_ALICUOTAS = '\n'.join(res)
