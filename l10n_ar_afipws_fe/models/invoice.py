# -*- coding: utf-8 -*-
from pyi25 import PyI25
from openerp import fields, models, api, _
from openerp.exceptions import Warning
from cStringIO import StringIO as StringIO
from pyafipws.soap import SoapFault
import logging
import sys
import traceback
_logger = logging.getLogger(__name__)


class invoice(models.Model):
    _inherit = "account.invoice"

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
    afip_barcode = fields.Char(
        compute='_get_barcode',
        string='AFIP Barcode'
        )
    afip_barcode_img = fields.Binary(
        compute='_get_barcode',
        string='AFIP Barcode Image'
        )
    afip_message = fields.Text(
        string='AFIP Message',
        copy=False,
        )
    afip_xml_request = fields.Text(
        string='AFIP XML Request',
        copy=False,
        )
    afip_xml_response = fields.Text(
        string='AFIP XML Response',
        copy=False,
        )
    afip_result = fields.Selection([
        ('', 'n/a'),
        ('A', 'Aceptado'),
        ('R', 'Rechazado'),
        ('O', 'Observado')],
        'Resultado',
        readonly=True,
        copy=False,
        help="AFIP request result")

    @api.one
    @api.depends('afip_cae')
    def _get_barcode(self):
        barcode = False
        if self.afip_cae:
            cae_due = ''.join(
                [c for c in str(self.afip_cae_due or '') if c.isdigit()])
            barcode = ''.join(
                [str(self.company_id.partner_id.vat[2:]),
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
    # def invoice_validate(self):
    def action_number(self):
        """
        We would prefere use invoice_validate or call request cae after
        action_number so that CAE is requested at the last part but raise error
        can not fall back the sequence next number.
        We want to add a inv._cr.commit() after sucesfuul cae request because
        we dont want to loose cae data because of a raise error on next steps
        but it doesn work as expected
        """
        self.do_pyafipws_request_cae()
        # self._cr.commit()
        res = super(invoice, self).action_number()
        return res

    @api.multi
    def do_pyafipws_request_cae(self):
        "Request to AFIP the invoices' Authorization Electronic Code (CAE)"
        for inv in self:
            # Ignore invoices with cae
            if inv.afip_cae and inv.afip_cae_due:
                continue

            afip_ws = self.journal_id.point_of_sale_id.afip_ws
            # Ignore invoice if not ws on point of sale
            if not afip_ws:
                continue

            # get the electronic invoice type, point of sale and afip_ws:
            journal = inv.journal_id
            point_of_sale = journal.point_of_sale_id
            pos_number = point_of_sale.number
            doc_afip_code = self.afip_document_class_id.afip_code

            # authenticate against AFIP:
            ws = self.company_id.get_connection(afip_ws).connect()

            next_invoice_number = inv.next_invoice_number

            # get the last invoice number registered in AFIP
            if afip_ws == "wsfe" or afip_ws == "wsmtxca":
                ws_invoice_number = ws.CompUltimoAutorizado(
                    doc_afip_code, pos_number)
            elif afip_ws == 'wsfex':
                ws_invoice_number = ws.GetLastCMP(
                    doc_afip_code, pos_number)

            ws_next_invoice_number = int(ws_invoice_number) + 1
            # verify that the invoice is the next one to be registered in AFIP
            if next_invoice_number != ws_next_invoice_number:
                raise Warning(_(
                    'Error!'
                    'Invoice id: %i'
                    'Next invoice number should be %i and not %i' % (
                        inv.id,
                        ws_next_invoice_number,
                        next_invoice_number)))

            commercial_partner = inv.commercial_partner_id
            partner_doc_code = commercial_partner.document_type_id.afip_code
            tipo_doc = partner_doc_code or '99'
            nro_doc = partner_doc_code and int(
                commercial_partner.document_number) or "0"
            cbt_desde = cbt_hasta = next_invoice_number
            concepto = inv.afip_concept

            fecha_cbte = inv.date_invoice
            if afip_ws != 'wsmtxca':
                fecha_cbte = fecha_cbte.replace("-", "")

            # due and billing dates only for concept "services"
            if int(concepto) != 1:
                fecha_venc_pago = inv.date_due
                fecha_serv_desde = inv.afip_service_start
                fecha_serv_hasta = inv.afip_service_end
                if afip_ws != 'wsmtxca':
                    fecha_venc_pago = fecha_venc_pago.replace("-", "")
                    fecha_serv_desde = fecha_serv_desde.replace("-", "")
                    fecha_serv_hasta = fecha_serv_hasta.replace("-", "")
            else:
                fecha_venc_pago = fecha_serv_desde = fecha_serv_hasta = None

            # # invoice amount totals:
            imp_total = str("%.2f" % abs(inv.amount_total))
            imp_tot_conc = "0.00"
            imp_neto = str("%.2f" % abs(inv.amount_untaxed))
            imp_iva = str("%.2f" % abs(inv.vat_amount))
            imp_subtotal = imp_neto  # TODO: not allways the case!
            imp_trib = str("%.2f" % abs(inv.other_taxes_amount))
            imp_op_ex = str("%.2f" % abs(inv.vat_exempt_amount))
            moneda_id = inv.currency_id.afip_code
            moneda_ctz = str(inv.currency_id.compute(
                1., inv.company_id.currency_id))

            # # foreign trade data: export permit, country code, etc.:
            # if invoice.pyafipws_incoterms:
            #     incoterms = invoice.pyafipws_incoterms.code
            #     incoterms_ds = invoice.pyafipws_incoterms.name
            # else:
            #     incoterms = incoterms_ds = None
            # if int(doc_afip_code) == 19 and tipo_expo == 1:
            #     permiso_existente =  "N" or "S"     # not used now
            # else:
            #     permiso_existente = ""
            obs_generales = inv.comment
            # if invoice.payment_term:
            #     forma_pago = invoice.payment_term.name
            #     obs_comerciales = invoice.payment_term.name
            # else:
            #     forma_pago = obs_comerciales = None
            # idioma_cbte = 1     # invoice language: spanish / español

            # # customer data (foreign trade):
            # nombre_cliente = invoice.partner_id.name
            # if invoice.partner_id.vat:
            #     if invoice.partner_id.vat.startswith("AR"):
            #         # use the Argentina AFIP's global CUIT for the country:
            #         cuit_pais_cliente = invoice.partner_id.vat[2:]
            #         id_impositivo = None
            #     else:
            #         # use the VAT number directly
            #         id_impositivo = invoice.partner_id.vat[2:] 
            #         # TODO: the prefix could be used to map the customer country
            #         cuit_pais_cliente = None
            # else:
            #     cuit_pais_cliente = id_impositivo = None
            # if invoice.address_invoice_id:
            #     domicilio_cliente = " - ".join([
            #                         invoice.address_invoice_id.name or '',
            #                         invoice.address_invoice_id.street or '',
            #                         invoice.address_invoice_id.street2 or '',
            #                         invoice.address_invoice_id.zip or '',
            #                         invoice.address_invoice_id.city or '',
            #                         ])
            # else:
            #     domicilio_cliente = ""
            # if invoice.address_invoice_id.country_id:
            #     # map ISO country code to AFIP destination country code:
            #     iso_code = invoice.address_invoice_id.country_id.code.lower()
            #     pais_dst_cmp = AFIP_COUNTRY_CODE_MAP[iso_code]

            # create the invoice internally in the helper
            if afip_ws == 'wsfe':
                ws.CrearFactura(
                    concepto, tipo_doc, nro_doc, doc_afip_code, pos_number,
                    cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                    imp_iva,
                    imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                    fecha_serv_desde, fecha_serv_hasta,
                    moneda_id, moneda_ctz
                    )
            elif afip_ws == 'wsmtxca':
                ws.CrearFactura(
                    concepto, tipo_doc, nro_doc, doc_afip_code, pos_number,
                    cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                    imp_subtotal,   # difference with wsfe
                    imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                    fecha_serv_desde, fecha_serv_hasta,
                    moneda_id, moneda_ctz,
                    obs_generales   # difference with wsfe
                    )
            # TODO implementar este
            # elif afip_ws == 'wsfex':
            #     ws.CrearFactura(doc_afip_code, pos_number, cbte_nro, fecha_cbte,
            #         imp_total, tipo_expo, permiso_existente, pais_dst_cmp, 
            #         nombre_cliente, cuit_pais_cliente, domicilio_cliente,
            #         id_impositivo, moneda_id, moneda_ctz, obs_comerciales, 
            #         obs_generales, forma_pago, incoterms, 
            #         idioma_cbte, incoterms_ds)
            for vat in self.vat_tax_ids:
                _logger.info('Adding VAT %s' % vat.tax_code_id.name)
                ws.AgregarIva(
                    vat.tax_code_id.afip_code,
                    "%.2f" % abs(vat.base_amount),
                    "%.2f" % abs(vat.tax_amount),
                    )
            for tax in self.not_vat_tax_ids:
                _logger.info('Adding TAX %s' % tax.tax_code_id.name)
                ws.AgregarTributo(
                    tax.tax_code_id.afip_code,
                    tax.tax_code_id.name,
                    "%.2f" % abs(vat.base_amount),
                    "%.2f" % abs(vat.tax_amount),
                    )

            # TODO tal vez en realidad solo hay que hacerlo para notas de
            # credito o determinados doc, ver pyafipws
            CbteAsoc = inv.get_related_invoices_data()[inv.id]
            if CbteAsoc:
                ws.AgregarCmpAsoc(
                    CbteAsoc['Tipo'],
                    CbteAsoc['PtoVta'],
                    CbteAsoc['Nro'],
                    )

            # analize line items - invoice detail
            # TODO implementar y mejorar aca
            if afip_ws == 'wsmtxca':
                raise Warning(_('AFIP WS %s not implemented yet') % afip_ws)
            # for line in invoice.invoice_line:
            #     codigo = line.product_id.code
            #     u_mtx = 1   # TODO: get it from uom?
            #     cod_mtx = line.product_id.ean13
            #     ds = line.name
            #     qty = line.quantity
            #     umed = 7    # TODO: line.uos_id...?
            #     precio = line.price_unit
            #     importe = line.price_subtotal
            #     bonif = line.discount or None
            #     if line.invoice_line_tax_id:
            #         iva_id = 5  # TODO: line.tax_code_id?
            #         imp_iva = importe * line.invoice_line_tax_id[0].amount
            #     else:
            #         iva_id = 1
            #         imp_iva = 0
            #     if afip_ws == 'wsmtxca':
            #         ws.AgregarItem(
            #             u_mtx, cod_mtx, codigo, ds, qty, umed,
            #             precio, bonif, iva_id, imp_iva, importe+imp_iva)
            #     elif afip_ws == 'wsfex':
            #         ws.AgregarItem(
            #             codigo, ds, qty, umed, precio, importe,
            #             bonif)

            # Request the authorization! (call the AFIP webservice method)
            vto = None
            msg = False
            try:
                if afip_ws == 'wsfe':
                    ws.CAESolicitar()
                    vto = ws.Vencimiento
                elif afip_ws == 'wsmtxca':
                    ws.AutorizarComprobante()
                    vto = ws.Vencimiento
                elif afip_ws == 'wsfex':
                    ws.Authorize(invoice.id)
                    vto = ws.FchVencCAE
            except SoapFault as fault:
                msg = 'Falla SOAP %s: %s' % (
                    fault.faultcode, fault.faultstring)
            except Exception, e:
                msg = e
            except Exception:
                if ws.Excepcion:
                    # get the exception already parsed by the helper
                    msg = ws.Excepcion
                else:
                    # avoid encoding problem when raising error
                    msg = traceback.format_exception_only(
                        sys.exc_type,
                        sys.exc_value)[0]
            if msg:
                raise Warning(_('AFIP Validation Error. %s' % msg))

            msg = u"\n".join([ws.Obs or "", ws.ErrMsg or ""])
            if not ws.CAE:
                raise Warning(_('AFIP Validation Error. %s' % msg))
            # TODO ver que algunso campos no tienen sentido porque solo se
            # escribe aca si no hay errores
            _logger.info('CAE solicitado con exito. CAE: %s. Resultado %s' %(
                ws.CAE, ws.Resultado))
            inv.write({
                'afip_cae': ws.CAE,
                'afip_cae_due': vto,
                'afip_result': ws.Resultado,
                'afip_message': msg,
                'afip_xml_request': ws.XmlRequest,
                'afip_xml_response': ws.XmlResponse,
                })

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
