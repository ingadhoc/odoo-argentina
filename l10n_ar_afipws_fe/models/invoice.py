# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from pyi25 import PyI25
from openerp import fields, models, api, _
from openerp.exceptions import Warning
from cStringIO import StringIO as StringIO
import logging
import sys
import traceback
_logger = logging.getLogger(__name__)

try:
    from pysimplesoap.client import SoapFault
except ImportError:
    _logger.debug('Can not `from pyafipws.soap import SoapFault`.')


class invoice(models.Model):
    _inherit = "account.invoice"

    afip_auth_verify_type = fields.Selection(
        related='company_id.afip_auth_verify_type',
        readonly=True,
    )
    afip_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True
    )
    afip_auth_verify_result = fields.Selection([
        ('A', 'Aprobado'), ('O', 'Observado'), ('R', 'Rechazado')],
        string='AFIP authorization verification result',
        copy=False,
        readonly=True,
    )
    afip_auth_verify_observation = fields.Char(
        string='AFIP authorization verification observation',
        copy=False,
        readonly=True,
    )
    afip_auth_mode = fields.Selection([
        ('CAE', 'CAE'), ('CAI', 'CAI'), ('CAEA', 'CAEA')],
        string='AFIP authorization mode',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    afip_auth_code = fields.Char(
        copy=False,
        string='CAE/CAI/CAEA Code',
        readonly=True,
        oldname='afip_cae',
        size=24,
        states={'draft': [('readonly', False)]},
    )
    afip_auth_code_due = fields.Date(
        copy=False,
        readonly=True,
        oldname='afip_cae_due',
        string='CAE/CAI/CAEA due Date',
        states={'draft': [('readonly', False)]},
    )
    # for compatibility
    afip_cae = fields.Char(
        related='afip_auth_code'
    )
    afip_cae_due = fields.Date(
        related='afip_auth_code_due'
    )

    afip_barcode = fields.Char(
        compute='_get_barcode',
        string=_('AFIP Barcode')
    )
    afip_barcode_img = fields.Binary(
        compute='_get_barcode',
        string=_('AFIP Barcode Image')
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
        states={'draft': [('readonly', False)]},
        copy=False,
        help="AFIP request result"
    )
    validation_type = fields.Char(
        'Validation Type',
        compute='get_validation_type',
    )

    @api.one
    def get_validation_type(self):
        # for compatibility with account_invoice_operation, if module installed
        # and there are operations we return no_validation so no validate
        # button is displayed
        if self._fields.get('operation_ids') and self.operation_ids:
            self.validation_type = 'no_validation'
        # if invoice has cae then me dont validate it against afip
        elif self.journal_id.point_of_sale_id.afip_ws and not self.afip_auth_code:
            self.validation_type = self.env[
                'res.company']._get_environment_type()

    @api.one
    @api.depends('afip_auth_code')
    def _get_barcode(self):
        barcode = False
        if self.afip_auth_code:
            cae_due = ''.join(
                [c for c in str(self.afip_auth_code_due or '') if c.isdigit()])
            barcode = ''.join(
                [str(self.company_id.partner_id.vat[2:]),
                    "%02d" % int(self.afip_document_class_id.afip_code),
                    "%04d" % int(self.journal_id.point_of_sale_id.number),
                    str(self.afip_auth_code), cae_due])
            barcode = barcode + self.verification_digit_modulo10(barcode)
        self.afip_barcode = barcode
        self.afip_barcode_img = self._make_image_I25(barcode)

    @api.model
    def _make_image_I25(self, barcode):
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
        return image

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
        """
        self.ensure_one()
        rel_invoices = self.search([
            ('number', '=', self.origin),
            ('state', 'not in',
                ['draft', 'proforma', 'proforma2', 'cancel'])])
        return rel_invoices

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
        self.check_afip_auth_verify_required()
        self.do_pyafipws_request_cae()
        # self._cr.commit()
        res = super(invoice, self).action_number()
        return res

    @api.multi
    def check_afip_auth_verify_required(self):
        for inv in self:
            if (
                    inv.type in ['in_invoice', 'in_refund'] and
                    inv.afip_auth_verify_type == 'required' and
                    inv.document_type in [
                        'invoice', 'debit_note', 'credit_note',
                        'receipt_invoice'] and
                    not inv.afip_auth_verify_result):
                raise Warning(_(
                    'You can not validate invoice as AFIP authorization '
                    'verification is required'))

    @api.multi
    def verify_on_afip(self):
        """
cbte_modo = "CAE"                    # modalidad de emision: CAI, CAE,
CAEA
cuit_emisor = "20267565393"          # proveedor
pto_vta = 4002                       # punto de venta habilitado en AFIP
cbte_tipo = 1                        # 1: factura A (ver tabla de parametros)
cbte_nro = 109                       # numero de factura
cbte_fch = "20131227"                # fecha en formato aaaammdd
imp_total = "121.0"                  # importe total
cod_autorizacion = "63523178385550"  # numero de CAI, CAE o CAEA
doc_tipo_receptor = 80               # CUIT (obligatorio Facturas A o M)
doc_nro_receptor = "30628789661"     # numero de CUIT del cliente

ok = wscdc.ConstatarComprobante(
    cbte_modo, cuit_emisor, pto_vta, cbte_tipo,
    cbte_nro, cbte_fch, imp_total, cod_autorizacion,
    doc_tipo_receptor, doc_nro_receptor)

print "Resultado:", wscdc.Resultado
print "Mensaje de Error:", wscdc.ErrMsg
print "Observaciones:", wscdc.Obs
        """
        afip_ws = "wscdc"
        ws = self.company_id.get_connection(afip_ws).connect()
        for inv in self:
            cbte_modo = inv.afip_auth_mode
            cod_autorizacion = inv.afip_auth_code
            if not cbte_modo or not cod_autorizacion:
                raise Warning(_(
                    'AFIP authorization mode and Code are required!'))

            # get issuer and receptor depending on supplier or customer invoice
            if inv.type in ['in_invoice', 'in_refund']:
                issuer = inv.commercial_partner_id
                receptor = inv.company_id.partner_id
            else:
                issuer = inv.company_id.partner_id
                receptor = inv.commercial_partner_id
            issuer_doc_code = str(issuer.document_type_id.afip_code)
            cuit_emisor = issuer.document_number
            if issuer_doc_code != '80' or not cuit_emisor:
                raise Warning(_('Issuer must have a CUIT configured'))

            receptor_doc_code = str(receptor.document_type_id.afip_code)
            doc_tipo_receptor = receptor_doc_code or '99'
            doc_nro_receptor = (
                receptor_doc_code and receptor.document_number or "0")
            afip_doc_class = inv.afip_document_class_id
            if (
                    afip_doc_class.document_letter_id.name in ['A', 'M'] and
                    doc_tipo_receptor != '80' or not doc_nro_receptor):
                    raise Warning(_(
                        'Para Comprobantes tipo A o tipo M:\n'
                        '*  el documento del receptor debe ser CUIT\n'
                        '*  el documento del Receptor es obligatorio\n'
                    ))

            cbte_nro = inv.invoice_number
            pto_vta = inv.point_of_sale
            cbte_tipo = afip_doc_class.afip_code
            if not pto_vta or not cbte_nro or not cbte_tipo:
                raise Warning(_(
                    'Point of sale and document number and document type '
                    'are required!'))
            cbte_fch = inv.date_invoice
            if not cbte_fch:
                raise Warning(_('Invoice Date is required!'))
            cbte_fch = cbte_fch.replace("-", "")
            imp_total = str("%.2f" % abs(inv.amount_total))

            _logger.info('Constatando Comprobante en afip')

            # atrapado de errores en afip
            msg = False
            try:
                ws.ConstatarComprobante(
                    cbte_modo, cuit_emisor, pto_vta, cbte_tipo, cbte_nro,
                    cbte_fch, imp_total, cod_autorizacion, doc_tipo_receptor,
                    doc_nro_receptor)
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
                raise Warning(_('AFIP Verification Error. %s' % msg))

            inv.write({
                'afip_auth_verify_result': ws.Resultado,
                'afip_auth_verify_observation': '%s%s' % (ws.Obs, ws.ErrMsg)
            })

    @api.multi
    def do_pyafipws_request_cae(self):
        "Request to AFIP the invoices' Authorization Electronic Code (CAE)"
        for inv in self:
            # Ignore invoices with cae
            if inv.afip_auth_code and inv.afip_auth_code_due:
                continue

            afip_ws = inv.journal_id.point_of_sale_id.afip_ws
            # Ignore invoice if not ws on point of sale
            if not afip_ws:
                continue

            # get the electronic invoice type, point of sale and afip_ws:
            commercial_partner = inv.commercial_partner_id
            country = commercial_partner.country_id
            journal = inv.journal_id
            point_of_sale = journal.point_of_sale_id
            pos_number = point_of_sale.number
            doc_afip_code = inv.afip_document_class_id.afip_code

            # authenticate against AFIP:
            ws = inv.company_id.get_connection(afip_ws).connect()

            next_invoice_number = inv.next_invoice_number

            # get the last invoice number registered in AFIP
            if afip_ws == "wsfe" or afip_ws == "wsmtxca":
                ws_invoice_number = ws.CompUltimoAutorizado(
                    doc_afip_code, pos_number)
            elif afip_ws == 'wsfex':
                ws_invoice_number = ws.GetLastCMP(
                    doc_afip_code, pos_number)
                if not country:
                    raise Warning(_(
                        'For WS "%s" country is required on partner' % (
                            afip_ws)))
                elif not country.code:
                    raise Warning(_(
                        'For WS "%s" country code is mandatory'
                        'Country: %s' % (
                            afip_ws, country.name)))
                elif not country.afip_code:
                    raise Warning(_(
                        'For WS "%s" country afip code is mandatory'
                        'Country: %s' % (
                            afip_ws, country.name)))

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

            partner_doc_code = commercial_partner.document_type_id.afip_code
            tipo_doc = partner_doc_code or '99'
            nro_doc = (
                partner_doc_code and commercial_partner.document_number or "0")
            cbt_desde = cbt_hasta = cbte_nro = next_invoice_number
            concepto = tipo_expo = int(inv.afip_concept)

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
            # ImpTotConc es el iva no gravado
            imp_tot_conc = str("%.2f" % abs(inv.vat_untaxed))
            # en la v9 lo hicimos diferente, aca restamos al vat amount
            # lo que seria exento y no gravado
            imp_neto = str("%.2f" % abs(
                inv.vat_base_amount - inv.vat_untaxed - inv.vat_exempt_amount))
            imp_iva = str("%.2f" % abs(inv.vat_amount))
            imp_subtotal = str("%.2f" % abs(inv.amount_untaxed))
            imp_trib = str("%.2f" % abs(inv.other_taxes_amount))
            imp_op_ex = str("%.2f" % abs(inv.vat_exempt_amount))
            moneda_id = inv.currency_id.afip_code
            moneda_ctz = inv.currency_rate
            # moneda_ctz = str(inv.company_id.currency_id.compute(
            # 1., inv.currency_id))

            # # foreign trade data: export permit, country code, etc.:
            if inv.afip_incoterm_id:
                incoterms = inv.afip_incoterm_id.afip_code
                incoterms_ds = inv.afip_incoterm_id.name
            else:
                incoterms = incoterms_ds = None
            if int(doc_afip_code) in [19, 20, 21] and tipo_expo == 1:
                permiso_existente = "N" or "S"     # not used now
            else:
                permiso_existente = ""
            obs_generales = inv.comment
            if inv.payment_term:
                forma_pago = inv.payment_term.name
                obs_comerciales = inv.payment_term.name
            else:
                forma_pago = obs_comerciales = None
            idioma_cbte = 1     # invoice language: spanish / español

            # customer data (foreign trade):
            nombre_cliente = commercial_partner.name
            # If argentinian and cuit, then use cuit
            if country.code == 'AR' and tipo_doc == 80 and nro_doc:
                id_impositivo = nro_doc
                cuit_pais_cliente = None
            # If not argentinian and vat, use vat
            elif country.code != 'AR' and commercial_partner.vat:
                id_impositivo = commercial_partner.vat[2:]
                cuit_pais_cliente = None
            # else use cuit pais cliente
            else:
                id_impositivo = None
                if commercial_partner.is_company:
                    cuit_pais_cliente = country.cuit_juridica
                else:
                    cuit_pais_cliente = country.cuit_fisica

            domicilio_cliente = " - ".join([
                                commercial_partner.name or '',
                                commercial_partner.street or '',
                                commercial_partner.street2 or '',
                                commercial_partner.zip or '',
                                commercial_partner.city or '',
            ])
            pais_dst_cmp = commercial_partner.country_id.afip_code

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
            elif afip_ws == 'wsfex':
                ws.CrearFactura(
                    doc_afip_code, pos_number, cbte_nro, fecha_cbte,
                    imp_total, tipo_expo, permiso_existente, pais_dst_cmp,
                    nombre_cliente, cuit_pais_cliente, domicilio_cliente,
                    id_impositivo, moneda_id, moneda_ctz, obs_comerciales,
                    obs_generales, forma_pago, incoterms,
                    idioma_cbte, incoterms_ds
                )

            # TODO ver si en realidad tenemos que usar un vat pero no lo
            # subimos
            if afip_ws != 'wsfex':
                for vat in inv.vat_tax_ids:
                    # we dont send no gravado y exento
                    if vat.tax_code_id.afip_code in [1, 2]:
                        continue
                    _logger.info('Adding VAT %s' % vat.tax_code_id.name)
                    # use instaed of "base_x" so it is not converted to
                    # company currency
                    ws.AgregarIva(
                        vat.tax_code_id.afip_code,
                        "%.2f" % abs(vat.base),
                        "%.2f" % abs(vat.amount),
                    )
                for tax in inv.not_vat_tax_ids:
                    _logger.info('Adding TAX %s' % tax.tax_code_id.name)
                    ws.AgregarTributo(
                        tax.tax_code_id.application_code,
                        tax.tax_code_id.name,
                        "%.2f" % abs(tax.base),
                        # como no tenemos la alicuota pasamos cero, en v9
                        # podremos pasar la alicuota
                        0,
                        "%.2f" % abs(tax.amount),
                    )

            CbteAsoc = inv.get_related_invoices_data()
            if CbteAsoc:
                ws.AgregarCmpAsoc(
                    CbteAsoc.afip_document_class_id.afip_code,
                    CbteAsoc.point_of_sale,
                    CbteAsoc.invoice_number,
                )

            # analize line items - invoice detail
            # wsfe do not require detail
            if afip_ws != 'wsfe':
                for line in inv.invoice_line:
                    codigo = line.product_id.code
                    # unidad de referencia del producto si se comercializa
                    # en una unidad distinta a la de consumo
                    if not line.uos_id.afip_code:
                        raise Warning(_('Not afip code con producto UOM %s' % (
                            line.uos_id.name)))
                    cod_mtx = line.uos_id.afip_code
                    ds = line.name
                    qty = line.quantity
                    umed = line.uos_id.afip_code
                    precio = line.price_unit
                    importe = line.price_subtotal
                    bonif = line.discount or None
                    if afip_ws == 'wsmtxca':
                        if not line.product_id.uom_id.afip_code:
                            raise Warning(_('Not afip code con producto UOM %s' % (
                                line.product_id.uom_id.name)))
                        u_mtx = line.product_id.uom_id.afip_code or line.uos_id.afip_code
                        if inv.invoice_id.type in ('out_invoice', 'in_invoice'):
                            iva_id = line.vat_tax_ids.tax_code_id.afip_code
                        else:
                            iva_id = line.vat_tax_ids.ref_tax_code_id.afip_code
                        vat_taxes_amounts = line.vat_tax_ids.compute_all(
                            line.price_unit, line.quantity,
                            product=line.product_id,
                            partner=inv.partner_id)
                        imp_iva = vat_taxes_amounts[
                            'total_included'] - vat_taxes_amounts['total']
                        ws.AgregarItem(
                            u_mtx, cod_mtx, codigo, ds, qty, umed,
                            precio, bonif, iva_id, imp_iva, importe + imp_iva)
                    elif afip_ws == 'wsfex':
                        ws.AgregarItem(
                            codigo, ds, qty, umed, precio, importe,
                            bonif)

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
                    ws.Authorize(inv.id)
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
            if not ws.CAE or ws.Resultado != 'A':
                raise Warning(_('AFIP Validation Error. %s' % msg))
            # TODO ver que algunso campos no tienen sentido porque solo se
            # escribe aca si no hay errores
            _logger.info('CAE solicitado con exito. CAE: %s. Resultado %s' % (
                ws.CAE, ws.Resultado))
            inv.write({
                'afip_auth_mode': 'CAE',
                'afip_auth_code': ws.CAE,
                'afip_auth_code_due': vto,
                'afip_result': ws.Resultado,
                'afip_message': msg,
                'afip_xml_request': ws.XmlRequest,
                'afip_xml_response': ws.XmlResponse,
            })

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
