##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from .pyi25 import PyI25
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
import logging
import sys
import traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

try:
    from pysimplesoap.client import SoapFault
except ImportError:
    _logger.debug('Can not `from pyafipws.soap import SoapFault`.')


class AccountInvoice(models.Model):
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
        compute='_compute_barcode',
        string='AFIP Barcode'
    )
    afip_barcode_img = fields.Binary(
        compute='_compute_barcode',
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
        states={'draft': [('readonly', False)]},
        copy=False,
        help="AFIP request result"
    )
    validation_type = fields.Char(
        'Validation Type',
        compute='_compute_validation_type',
    )

    @api.depends('journal_id', 'afip_auth_code')
    def _compute_validation_type(self):
        for rec in self:
            if rec.journal_id.afip_ws and not rec.afip_auth_code:
                validation_type = self.env[
                    'res.company']._get_environment_type()
                # if we are on homologation env and we dont have certificates
                # we validate only locally
                if validation_type == 'homologation':
                    try:
                        rec.company_id.get_key_and_certificate(validation_type)
                    except Exception:
                        validation_type = False
                rec.validation_type = validation_type

    @api.multi
    @api.depends('afip_auth_code')
    def _compute_barcode(self):
        for rec in self:
            barcode = False
            if rec.afip_auth_code:
                cae_due = ''.join(
                    [c for c in str(
                        rec.afip_auth_code_due or '') if c.isdigit()])
                barcode = ''.join(
                    [str(rec.company_id.cuit),
                        "%02d" % int(rec.document_type_id.code),
                        "%04d" % int(rec.journal_id.point_of_sale_number),
                        str(rec.afip_auth_code), cae_due])
                barcode = barcode + rec.verification_digit_modulo10(barcode)
            rec.afip_barcode = barcode
            rec.afip_barcode_img = rec._make_image_I25(barcode)

    @api.model
    def _make_image_I25(self, barcode):
        "Generate the required barcode Interleaved of 7 image using PIL"
        image = False
        if barcode:
            # create the helper:
            pyi25 = PyI25()
            output = BytesIO()
            # call the helper:
            bars = ''.join([c for c in barcode if c.isdigit()])
            if not bars:
                bars = "00"
            pyi25.GenerarImagen(bars, output, extension="PNG")
            # get the result and encode it for openerp binary field:
            image = base64.b64encode(output.getvalue())
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
        digito = 10 - (etapa4 - (int(etapa4 // 10) * 10))
        if digito == 10:
            digito = 0
        return str(digito)

    @api.multi
    def get_related_invoices_data(self):
        """
        List related invoice information to fill CbtesAsoc.
        """
        self.ensure_one()
        # for now we only get related document for debit and credit notes
        # because, for eg, an invoice can not be related to an invocie and
        # that happens if you choose the modify option of the credit note
        # wizard. A mapping of which documents can be reported as related
        # documents would be a better solution
        if self.document_type_internal_type in ['debit_note', 'credit_note'] \
                and self.origin:
            return self.search([
                ('commercial_partner_id', '=', self.commercial_partner_id.id),
                ('company_id', '=', self.company_id.id),
                ('document_number', '=', self.origin),
                ('state', 'not in',
                    ['draft', 'proforma', 'proforma2', 'cancel'])],
                limit=1)
        else:
            return self.browse()

    @api.multi
    def invoice_validate(self):
        """
        The last thing we do is request the cae because if an error occurs
        after cae requested, the invoice has been already validated on afip
        """
        res = super(AccountInvoice, self).invoice_validate()
        self.check_afip_auth_verify_required()
        self.do_pyafipws_request_cae()
        return res

    @api.multi
    # para cuando se crea, por ej, desde ventas o contratos
    @api.constrains('partner_id')
    # para cuando se crea manualmente la factura
    @api.onchange('partner_id')
    def _set_afip_journal(self):
        """
        Si es factura electrónica y es del exterior, buscamos diario
        para exportación
        TODO: implementar similar para elegir bono fiscal o factura con detalle
        """
        for rec in self.filtered(lambda x: (
                x.journal_id.point_of_sale_type == 'electronic' and
                x.journal_id.type == 'sale')):

            res_code = rec.commercial_partner_id.afip_responsability_type_id.\
                code
            ws = rec.journal_id.afip_ws
            journal = self.env['account.journal']
            domain = [
                ('company_id', '=', rec.company_id.id),
                ('point_of_sale_type', '=', 'electronic'),
                ('type', '=', 'sale'),
            ]
            # TODO mejorar que aca buscamos por codigo de resp mientras que
            # el mapeo de tipo de documentos es configurable por letras y,
            # por ejemplo, si se da letra e de RI a RI y se genera factura
            # para un RI queriendo forzar diario de expo, termina dando error
            # porque los ws y los res_code son incompatibles para esta logica.
            # El error lo da el metodo check_journal_document_type_journal
            # porque este metodo trata de poner otro diario sin actualizar
            # el tipo de documento
            if ws == 'wsfe' and res_code in ['8', '9', '10']:
                domain.append(('afip_ws', '=', 'wsfex'))
                journal = journal.search(domain, limit=1)
            elif ws == 'wsfex' and res_code not in ['8', '9', '10']:
                domain.append(('afip_ws', '=', 'wsfe'))
                journal = journal.search(domain, limit=1)

            if journal:
                rec.journal_id = journal.id

    @api.multi
    def check_afip_auth_verify_required(self):
        for inv in self:
            if (
                    inv.type in ['in_invoice', 'in_refund'] and
                    inv.afip_auth_verify_type == 'required' and
                    inv.document_type_internal_type in [
                        'invoice', 'debit_note', 'credit_note',
                        'receipt_invoice'] and
                    not inv.afip_auth_verify_result):
                raise UserError(_(
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
                raise UserError(_(
                    'AFIP authorization mode and Code are required!'))

            # get issuer and receptor depending on supplier or customer invoice
            if inv.type in ['in_invoice', 'in_refund']:
                issuer = inv.commercial_partner_id
                receptor = inv.company_id.partner_id
            else:
                issuer = inv.company_id.partner_id
                receptor = inv.commercial_partner_id

            cuit_emisor = issuer.cuit_required()

            receptor_doc_code = str(receptor.main_id_category_id.afip_code)
            doc_tipo_receptor = receptor_doc_code or '99'
            doc_nro_receptor = (
                receptor_doc_code and receptor.main_id_number or "0")
            doc_type = inv.document_type_id
            if (
                    doc_type.document_letter_id.name in ['A', 'M'] and
                    doc_tipo_receptor != '80' or not doc_nro_receptor):
                    raise UserError(_(
                        'Para Comprobantes tipo A o tipo M:\n'
                        '*  el documento del receptor debe ser CUIT\n'
                        '*  el documento del Receptor es obligatorio\n'
                    ))

            cbte_nro = inv.invoice_number
            pto_vta = inv.point_of_sale_number
            cbte_tipo = doc_type.code
            if not pto_vta or not cbte_nro or not cbte_tipo:
                raise UserError(_(
                    'Point of sale and document number and document type '
                    'are required!'))
            cbte_fch = inv.date_invoice
            if not cbte_fch:
                raise UserError(_('Invoice Date is required!'))
            cbte_fch = cbte_fch.replace("-", "")
            imp_total = str("%.2f" % inv.amount_total)

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
            except Exception as e:
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
                raise UserError(_('AFIP Verification Error. %s' % msg))

            inv.write({
                'afip_auth_verify_result': ws.Resultado,
                'afip_auth_verify_observation': '%s%s' % (ws.Obs, ws.ErrMsg)
            })

    @api.multi
    def do_pyafipws_request_cae(self):
        "Request to AFIP the invoices' Authorization Electronic Code (CAE)"
        for inv in self:
            # Ignore invoices with cae (do not check date)
            if inv.afip_auth_code:
                continue

            if inv.journal_id.point_of_sale_type != 'electronic':
                continue
            afip_ws = inv.journal_id.afip_ws
            # Ignore invoice if not ws on point of sale
            if not afip_ws:
                raise UserError(_(
                    'If you use electronic journals (invoice id %s) you need '
                    'configure AFIP WS on the journal') % (inv.id))

            # if no validation type and we are on electronic invoice, it means
            # that we are on a testing database without homologation
            # certificates
            if not inv.validation_type:
                msg = (
                    'Factura validada solo localmente por estar en ambiente '
                    'de homologación sin claves de homologación')
                inv.write({
                    'afip_auth_mode': 'CAE',
                    'afip_auth_code': '68448767638166',
                    'afip_auth_code_due': inv.date_invoice,
                    'afip_result': '',
                    'afip_message': msg,
                })
                inv.message_post(msg)
                continue

            # get the electronic invoice type, point of sale and afip_ws:
            commercial_partner = inv.commercial_partner_id
            country = commercial_partner.country_id
            journal = inv.journal_id
            pos_number = journal.point_of_sale_number
            doc_afip_code = inv.document_type_id.code

            # authenticate against AFIP:
            ws = inv.company_id.get_connection(afip_ws).connect()

            if afip_ws == 'wsfex':
                if not country:
                    raise UserError(_(
                        'For WS "%s" country is required on partner' % (
                            afip_ws)))
                elif not country.code:
                    raise UserError(_(
                        'For WS "%s" country code is mandatory'
                        'Country: %s' % (
                            afip_ws, country.name)))
                elif not country.afip_code:
                    raise UserError(_(
                        'For WS "%s" country afip code is mandatory'
                        'Country: %s' % (
                            afip_ws, country.name)))

            ws_next_invoice_number = int(
                inv.journal_document_type_id.get_pyafipws_last_invoice(
                )['result']) + 1
            # verify that the invoice is the next one to be registered in AFIP
            if inv.invoice_number != ws_next_invoice_number:
                raise UserError(_(
                    'Error!'
                    'Invoice id: %i'
                    'Next invoice number should be %i and not %i' % (
                        inv.id,
                        ws_next_invoice_number,
                        inv.invoice_number)))

            partner_id_code = commercial_partner.main_id_category_id.afip_code
            tipo_doc = partner_id_code or '99'
            nro_doc = partner_id_code and int(
                commercial_partner.main_id_number) or "0"
            cbt_desde = cbt_hasta = cbte_nro = inv.invoice_number
            concepto = tipo_expo = int(inv.afip_concept)

            fecha_cbte = inv.date_invoice
            if afip_ws != 'wsmtxca':
                fecha_cbte = fecha_cbte.replace("-", "")

            mipyme_fce = int(doc_afip_code) in [
                201, 202, 203, 206, 207, 208, 211, 212, 213]

            # due date only for concept "services" and mipyme_fce
            if int(concepto) != 1 or mipyme_fce:
                fecha_venc_pago = inv.date_due or inv.date_invoice
                if afip_ws != 'wsmtxca':
                    fecha_venc_pago = fecha_venc_pago.replace("-", "")
            else:
                fecha_venc_pago = None

            # fecha de servicio solo si no es 1
            if int(concepto) != 1:
                fecha_serv_desde = inv.afip_service_start
                fecha_serv_hasta = inv.afip_service_end
                if afip_ws != 'wsmtxca':
                    fecha_serv_desde = fecha_serv_desde.replace("-", "")
                    fecha_serv_hasta = fecha_serv_hasta.replace("-", "")
            else:
                fecha_serv_desde = fecha_serv_hasta = None

            # # invoice amount totals:
            imp_total = str("%.2f" % inv.amount_total)
            # ImpTotConc es el iva no gravado
            imp_tot_conc = str("%.2f" % inv.vat_untaxed_base_amount)
            # tal vez haya una mejor forma, la idea es que para facturas c
            # no se pasa iva. Probamos hacer que vat_taxable_amount
            # incorpore a los imp cod 0, pero en ese caso termina reportando
            # iva y no lo queremos
            if inv.document_type_id.document_letter_id.name == 'C':
                imp_neto = str("%.2f" % inv.amount_untaxed)
            else:
                imp_neto = str("%.2f" % inv.vat_taxable_amount)
            imp_iva = str("%.2f" % inv.vat_amount)
            # se usaba para wsca..
            # imp_subtotal = str("%.2f" % inv.amount_untaxed)
            imp_trib = str("%.2f" % inv.other_taxes_amount)
            imp_op_ex = str("%.2f" % inv.vat_exempt_base_amount)
            moneda_id = inv.currency_id.afip_code
            moneda_ctz = inv.currency_rate

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
                if mipyme_fce:
                    # agregamos cbu para factura de credito electronica
                    ws.AgregarOpcional(
                        opcional_id=2101,
                        valor=inv.partner_bank_id.cbu)
            # elif afip_ws == 'wsmtxca':
            #     obs_generales = inv.comment
            #     ws.CrearFactura(
            #         concepto, tipo_doc, nro_doc, doc_afip_code, pos_number,
            #         cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
            #         imp_subtotal,   # difference with wsfe
            #         imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
            #         fecha_serv_desde, fecha_serv_hasta,
            #         moneda_id, moneda_ctz,
            #         obs_generales   # difference with wsfe
            #     )
            elif afip_ws == 'wsfex':
                # # foreign trade data: export permit, country code, etc.:
                if inv.afip_incoterm_id:
                    incoterms = inv.afip_incoterm_id.afip_code
                    incoterms_ds = inv.afip_incoterm_id.name
                    # máximo de 20 caracteres admite
                    incoterms_ds = incoterms_ds and incoterms_ds[:20]
                else:
                    incoterms = incoterms_ds = None
                # por lo que verificamos, se pide permiso existente solo
                # si es tipo expo 1 y es factura (codigo 19), para todo el
                # resto pasamos cadena vacia
                if int(doc_afip_code) == 19 and tipo_expo == 1:
                    # TODO investigar si hay que pasar si ("S")
                    permiso_existente = "N"
                else:
                    permiso_existente = ""
                obs_generales = inv.comment

                if inv.payment_term_id:
                    forma_pago = inv.payment_term_id.name
                    obs_comerciales = inv.payment_term_id.name
                else:
                    forma_pago = obs_comerciales = None

                idioma_cbte = 1     # invoice language: spanish / español

                # TODO tal vez podemos unificar este criterio con el del
                # citi que pide el cuit al partner
                # customer data (foreign trade):
                nombre_cliente = commercial_partner.name
                # If argentinian and cuit, then use cuit
                if country.code == 'AR' and tipo_doc == 80 and nro_doc:
                    id_impositivo = nro_doc
                    cuit_pais_cliente = None
                # If not argentinian and vat, use vat
                elif country.code != 'AR' and nro_doc:
                    id_impositivo = nro_doc
                    cuit_pais_cliente = None
                # else use cuit pais cliente
                else:
                    id_impositivo = None
                    if commercial_partner.is_company:
                        cuit_pais_cliente = country.cuit_juridica
                    else:
                        cuit_pais_cliente = country.cuit_fisica
                    if not cuit_pais_cliente:
                        raise UserError(_(
                            'No vat defined for the partner and also no CUIT '
                            'set on country'))

                domicilio_cliente = " - ".join([
                    commercial_partner.name or '',
                    commercial_partner.street or '',
                    commercial_partner.street2 or '',
                    commercial_partner.zip or '',
                    commercial_partner.city or '',
                ])
                pais_dst_cmp = commercial_partner.country_id.afip_code
                ws.CrearFactura(
                    doc_afip_code, pos_number, cbte_nro, fecha_cbte,
                    imp_total, tipo_expo, permiso_existente, pais_dst_cmp,
                    nombre_cliente, cuit_pais_cliente, domicilio_cliente,
                    id_impositivo, moneda_id, moneda_ctz, obs_comerciales,
                    obs_generales, forma_pago, incoterms,
                    idioma_cbte, incoterms_ds
                )
            elif afip_ws == 'wsbfe':
                zona = 1  # Nacional (la unica devuelta por afip)
                # los responsables no inscriptos no se usan mas
                impto_liq_rni = 0.0
                imp_iibb = sum(inv.tax_line_ids.filtered(lambda r: (
                    r.tax_id.tax_group_id.type == 'perception' and
                    r.tax_id.tax_group_id.application == 'provincial_taxes')
                ).mapped('amount'))
                imp_perc_mun = sum(inv.tax_line_ids.filtered(lambda r: (
                    r.tax_id.tax_group_id.type == 'perception' and
                    r.tax_id.tax_group_id.application == 'municipal_taxes')
                ).mapped('amount'))
                imp_internos = sum(inv.tax_line_ids.filtered(
                    lambda r: r.tax_id.tax_group_id.application == 'others'
                ).mapped('amount'))
                imp_perc = sum(inv.tax_line_ids.filtered(lambda r: (
                    r.tax_id.tax_group_id.type == 'perception' and
                    # r.tax_id.tax_group_id.tax != 'vat' and
                    r.tax_id.tax_group_id.application == 'national_taxes')
                ).mapped('amount'))

                ws.CrearFactura(
                    tipo_doc, nro_doc, zona, doc_afip_code, pos_number,
                    cbte_nro, fecha_cbte, imp_total, imp_neto, imp_iva,
                    imp_tot_conc, impto_liq_rni, imp_op_ex, imp_perc, imp_iibb,
                    imp_perc_mun, imp_internos, moneda_id, moneda_ctz
                )

            # TODO ver si en realidad tenemos que usar un vat pero no lo
            # subimos
            if afip_ws not in ['wsfex', 'wsbfe']:
                for vat in inv.vat_taxable_ids:
                    _logger.info(
                        'Adding VAT %s' % vat.tax_id.tax_group_id.name)
                    ws.AgregarIva(
                        vat.tax_id.tax_group_id.afip_code,
                        "%.2f" % vat.base,
                        # "%.2f" % abs(vat.base_amount),
                        "%.2f" % vat.amount,
                    )

                for tax in inv.not_vat_tax_ids:
                    _logger.info(
                        'Adding TAX %s' % tax.tax_id.tax_group_id.name)
                    ws.AgregarTributo(
                        tax.tax_id.tax_group_id.application_code,
                        tax.tax_id.tax_group_id.name,
                        "%.2f" % tax.base,
                        # "%.2f" % abs(tax.base_amount),
                        # TODO pasar la alicuota
                        # como no tenemos la alicuota pasamos cero, en v9
                        # podremos pasar la alicuota
                        0,
                        "%.2f" % tax.amount,
                    )

            CbteAsoc = inv.get_related_invoices_data()
            # bono no tiene implementado AgregarCmpAsoc
            if CbteAsoc and afip_ws != 'wsbfe':
                ws.AgregarCmpAsoc(
                    CbteAsoc.document_type_id.code,
                    CbteAsoc.point_of_sale_number,
                    CbteAsoc.invoice_number,
                )

            # analize line items - invoice detail
            # wsfe do not require detail
            if afip_ws != 'wsfe':
                for line in inv.invoice_line_ids:
                    codigo = line.product_id.default_code
                    # unidad de referencia del producto si se comercializa
                    # en una unidad distinta a la de consumo
                    if not line.uom_id.afip_code:
                        raise UserError(_(
                            'Not afip code con producto UOM %s' % (
                                line.uom_id.name)))
                    # cod_mtx = line.uom_id.afip_code
                    ds = line.name
                    qty = line.quantity
                    umed = line.uom_id.afip_code
                    precio = line.price_unit
                    importe = line.price_subtotal
                    # calculamos bonificacion haciendo teorico menos importe
                    bonif = line.discount and str(
                        "%.2f" % (precio * qty - importe)) or None
                    if afip_ws in ['wsmtxca', 'wsbfe']:
                        if not line.product_id.uom_id.afip_code:
                            raise UserError(_(
                                'Not afip code con producto UOM %s' % (
                                    line.product_id.uom_id.name)))
                        # u_mtx = (
                        #     line.product_id.uom_id.afip_code or
                        #     line.uom_id.afip_code)
                        iva_id = line.vat_tax_id.tax_group_id.afip_code
                        vat_taxes_amounts = line.vat_tax_id.compute_all(
                            line.price_unit, inv.currency_id, line.quantity,
                            product=line.product_id,
                            partner=inv.partner_id)
                        imp_iva = sum(
                            [x['amount'] for x in vat_taxes_amounts['taxes']])
                        if afip_ws == 'wsmtxca':
                            raise UserError(
                                _('WS wsmtxca Not implemented yet'))
                            # ws.AgregarItem(
                            #     u_mtx, cod_mtx, codigo, ds, qty, umed,
                            #     precio, bonif, iva_id, imp_iva,
                            #     importe + imp_iva)
                        elif afip_ws == 'wsbfe':
                            sec = ""  # Código de la Secretaría (TODO usar)
                            ws.AgregarItem(
                                codigo, sec, ds, qty, umed, precio, bonif,
                                iva_id, importe + imp_iva)
                    elif afip_ws == 'wsfex':
                        ws.AgregarItem(
                            codigo, ds, qty, umed, precio, "%.2f" % importe,
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
                elif afip_ws == 'wsbfe':
                    ws.Authorize(inv.id)
                    vto = ws.Vencimiento
            except SoapFault as fault:
                msg = 'Falla SOAP %s: %s' % (
                    fault.faultcode, fault.faultstring)
            except Exception as e:
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
                raise UserError(_('AFIP Validation Error. %s' % msg))

            msg = u"\n".join([ws.Obs or "", ws.ErrMsg or ""])
            if not ws.CAE or ws.Resultado != 'A':
                raise UserError(_('AFIP Validation Error. %s' % msg))
            # TODO ver que algunso campos no tienen sentido porque solo se
            # escribe aca si no hay errores
            _logger.info('CAE solicitado con exito. CAE: %s. Resultado %s' % (
                ws.CAE, ws.Resultado))
            if afip_ws == 'wsbfe':
                vto = datetime.strftime(
                    datetime.strptime(vto, '%d/%m/%Y'), '%Y%m%d')
            inv.write({
                'afip_auth_mode': 'CAE',
                'afip_auth_code': ws.CAE,
                'afip_auth_code_due': vto,
                'afip_result': ws.Resultado,
                'afip_message': msg,
                'afip_xml_request': ws.XmlRequest,
                'afip_xml_response': ws.XmlResponse,
            })
            # si obtuvimos el cae hacemos el commit porque estoya no se puede
            # volver atras
            # otra alternativa seria escribir con otro cursor el cae y que
            # la factura no quede validada total si tiene cae no se vuelve a
            # solicitar. Lo mismo podriamos usar para grabar los mensajes de
            # afip de respuesta
            inv._cr.commit()
