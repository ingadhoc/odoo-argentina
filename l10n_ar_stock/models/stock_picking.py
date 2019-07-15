from odoo import models, fields, api, _
import datetime
# import odoo.tools as tools
try:
    from pyafipws.iibb import IIBB
except ImportError:
    IIBB = None
from odoo.exceptions import UserError,ValidationError
# import tempfile
import os
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):

    _inherit = "stock.picking"

    document_type_id = fields.Many2one(
        related='book_id.document_type_id',
        readonly=True
    )
    cot_numero_unico = fields.Char(
        'COT - Nro Único',
        help='Número único del último COT solicitado',
    )
    cot_numero_comprobante = fields.Char(
        'COT - Nro Comprobante',
        help='Número de comprobante del último COT solicitado',
    )

    @api.multi
    def get_arba_file_data(
            self, datetime_out, tipo_recorrido, carrier_partner,
            patente_vehiculo, patente_acomplado, prod_no_term_dev, importe):
        """
        NOTA: esta implementado como para soportar seleccionar varios remitos
        y mandarlos juntos pero por ahora no le estamos dando uso.
        Tener en cuenta que si se numera con más de un remito nosotros mandamos
        solo el primero ya que para cada remito reportado se debe indicar
        los productos y ese dato no lo tenemos (solo sabemos cuantas hojas
        consume)
        """

        FECHA_SALIDA_TRANSPORTE = datetime_out.strftime('%Y%m%d')
        HORA_SALIDA_TRANSPORTE = datetime_out.strftime('%H%M')

        company = self.mapped('company_id')
        if len(company) > 1:
            raise UserError(_(
                'Los remitos seleccionados deben pertenecer a la misma '
                'compañía'))
        cuit = company.cuit_required()
        cuit_carrier = carrier_partner.cuit_required()

        if cuit_carrier == cuit and not patente_vehiculo:
            raise UserError(_(
                'Si el CUIT de la compañía y el cuit del transportista son el '
                'mismo, se debe informar la patente del vehículo.'))

        # ej. nombre archivo TB_30111111118_003002_20060716_000183.txt
        # TODO ver de donde obtener estos datos
        nro_planta = '000'
        nro_puerta = '000'
        nro_secuencial = self.env['ir.sequence'].with_context(
            force_company=company.id).next_by_code('arba.cot.file')
        if not nro_secuencial:
            raise UserError(_(
                'No sequence found for COT files (code = "arba.cot.file") on '
                'company "%s') % (company.name))

        filename = "TB_%s_%s%s_%s_%s.txt" % (
            str(cuit),
            str(nro_planta),
            str(nro_puerta),
            str(datetime.date.today().strftime('%Y%m%d')),
            str(nro_secuencial))

        # 01 - HEADER: TIPO_REGISTRO & CUIT_EMPRESA
        HEADER = ["01", cuit]

        # 04 - FOOTER (Pie): TIPO_REGISTRO: 04 & CANTIDAD_TOTAL_REMITOS
        # TODO que tome 10 caracteres
        FOOTER = ["04", str(len(self))]

        # TODO, si interesa se puede repetir esto para cada uno
        REMITOS_PRODUCTOS = []

        # recorremos cada voucher number de cada remito
        # for voucher in self.mapped('voucher_ids'):
        #     rec = voucher.picking_id
        for rec in self:
            if not rec.voucher_ids:
                raise UserError(_('No se asignó número de remito'))
            voucher = rec.voucher_ids[0]
            dest_partner = rec.partner_id
            source_partner = rec.picking_type_id.warehouse_id.partner_id or\
                rec.company_id.partner_id
            commercial_partner = dest_partner.commercial_partner_id

            if not source_partner.state_id.code or \
                    not dest_partner.state_id.code:
                raise UserError(_(
                    'Las provincias de origen y destino son obligatorias y '
                    'deben tener un código válido'))

            if not rec.document_type_id:
                raise UserError(_(
                    'Picking has no "Document type" linked (Id: %s') % (
                    rec.id))
            validator = rec.document_type_id.validator_id
            CODIGO_DGI = rec.document_type_id.code
            letter = rec.document_type_id.document_letter_id
            if not validator or not CODIGO_DGI or not letter:
                raise UserError(_(
                    'Document type has no validator, code or letter configured'
                    ' (Id: %s') % (rec.document_type_id.id))

            # TODO ver de hacer uno por número de remito?
            PREFIJO, NUMERO = validator.validate_value(
                voucher.name, return_parts=True)

            # rellenar y truncar a 2
            TIPO = '{:>2.2}'.format(letter.name)

            # si nro doc y tipo en ‘DNI’, ‘LC’, ‘LE’, ‘PAS’, ‘CI’ y doc
            doc_categ_id = commercial_partner.main_id_category_id
            if commercial_partner.main_id_number and doc_categ_id.code in [
                    'DNI', 'LC', 'LE', 'PAS', 'CI']:
                dest_tipo_doc = doc_categ_id.code
                dest_doc = commercial_partner.main_id_number
            else:
                dest_tipo_doc = ''
                dest_doc = ''

            dest_tipo_doc = dest_tipo_doc
            dest_doc = dest_doc

            dest_cons_final = commercial_partner.\
                afip_responsability_type_id.id == "5" and '1' or '0'

            dest_cuit = commercial_partner.cuit

            REMITOS_PRODUCTOS.append([
                "02",  # TIPO_REGISTRO

                # FECHA_EMISION
                # fields.Date.from_string(self.date_done).strftime('%Y%m%d').
                datetime.date.today().strftime('%Y%m%d'),

                # CODIGO_UNICO formato (CODIGO_DGI, TIPO, PREFIJO, NUMERO)
                # ej. 91 |R999900068148|
                "%s%s%s%s" % (CODIGO_DGI, TIPO, PREFIJO, NUMERO),

                # FECHA_SALIDA_TRANSPORTE: formato AAAAMMDD
                FECHA_SALIDA_TRANSPORTE,

                # HORA_SALIDA_TRANSPORTE: formato HHMM
                HORA_SALIDA_TRANSPORTE,

                # SUJETO_GENERADOR: 'E' emisor, 'D' destinatario
                'E',

                # DESTINATARIO_CONSUMIDOR_FINAL: 0 no, 1 sí
                dest_cons_final,

                # DESTINATARIO_TIPO_DOCUMENTO: 'DNI', 'LE', 'PAS', 'CI'
                dest_tipo_doc,

                # DESTINATARIO_DOCUMENTO
                dest_doc,

                # DESTIANTARIO_CUIT
                dest_cuit,

                # DESTINATARIO_RAZON_SOCIAL
                commercial_partner.name[:50],

                # DESTINATARIO_TENEDOR: 0=no, 1=si.
                dest_cons_final and '0' or '1',

                # DESTINO_DOMICILIO_CALLE
                (dest_partner.street or '')[:40],

                # DESTINO_DOMICILIO_NUMERO
                # TODO implementar
                '',

                # DESTINO_DOMICILIO_COMPLE
                # TODO implementar valores ’ ’, ‘S/N’ , ‘1/2’, ‘1/4’, ‘BIS’
                'S/N',

                # DESTINO_DOMICILIO_PISO
                # TODO implementar
                '',

                # DESTINO_DOMICILIO_DTO
                # TODO implementar
                '',

                # DESTINO_DOMICILIO_BARRIO
                # TODO implementar
                '',

                # DESTINO_DOMICILIO_CODIGOP
                (dest_partner.zip or '')[:8],

                # DESTINO_DOMICILIO_LOCALIDAD
                (dest_partner.city or '')[:50],

                # DESTINO_DOMICILIO_PROVINCIA: ver tabla de provincias
                # usa código distinto al de afip
                (dest_partner.state_id.code or '')[:1],

                # PROPIO_DESTINO_DOMICILIO_CODIGO
                # TODO implementar
                '',

                # ENTREGA_DOMICILIO_ORIGEN: 'SI' o 'NO'
                # TODO implementar
                'NO',

                # ORIGEN_CUIT
                cuit,

                # ORIGEN_RAZON_SOCIAL
                company.name[:50],

                # EMISOR_TENEDOR: 0=no, 1=si
                # TODO implementar
                '0',

                # ORIGEN_DOMICILIO_CALLE
                (source_partner.street or '')[:40],

                # ORIGEN DOMICILIO_NUMBERO
                # TODO implementar
                '',

                # ORIGEN_DOMICILIO_COMPLE
                # TODO implementar valores ’ ’, ‘S/N’ , ‘1/2’, ‘1/4’, ‘BIS’
                'S/N',

                # ORIGEN_DOMICILIO_PISO
                # TODO implementar
                '',

                # ORIGEN_DOMICILIO_DTO
                # TODO implementar
                '',

                # ORIGEN_DOMICILIO_BARRIO
                # TODO implementar
                '',

                # ORIGEN_DOMICILIO_CODIGOP
                (source_partner.zip or '')[:8],

                # ORIGEN_DOMICILIO_LOCALIDAD
                (source_partner.city or '')[:50],

                # ORIGEN_DOMICILIO_PROVINCIA: ver tabla de provincias
                (source_partner.state_id.code or '')[:1],

                # TRANSPORTISTA_CUIT
                cuit_carrier,

                # TIPO_RECORRIDO: 'U' urbano, 'R' rural, 'M' mixto
                tipo_recorrido,

                # RECORRIDO_LOCALIDAD: máx. 50 caracteres,
                # TODO implementar
                '',

                # RECORRIDO_CALLE: máx. 40 caracteres
                # TODO implementar
                '',

                # RECORRIDO_RUTA: máx. 40 caracteres
                # TODO implementar
                '',

                # PATENTE_VEHICULO: 3 letras y 3 números
                patente_vehiculo or '',

                # PATENTE_ACOPLADO: 3 letras y 3 números
                patente_acomplado or '',

                # PRODUCTO_NO_TERM_DEV: 0=No, 1=Si (devoluciones)
                prod_no_term_dev,

                # IMPORTE: formato 8 enteros 2 decimales,
                str(int(round(importe * 100.0)))[-10:],
            ])

            for line in rec.mapped('move_line_ids'):

                # buscamos si hay unidad de medida de la cateogria que tenga
                # codigo de arba y usamos esa, ademas convertimos la cantidad
                product_qty = line.product_qty
                if line.product_uom_id.arba_code:
                    uom_arba_with_code = line.product_uom_id
                else:
                    uom_arba_with_code = line.product_uom_id.search([
                        ('category_id', '=',
                            line.product_uom_id.category_id.id),
                        ('arba_code', '!=', False)], limit=1)
                    if not uom_arba_with_code:
                        raise UserError(_(
                            'No arba code for uom "%s" (Id: %s) or any uom in '
                            'category "%s"') % (
                            line.product_uom_id.name, line.product_uom_id.id,
                            line.product_uom_id.category_id.name))

                    product_qty = line.product_uom_id._compute_qty(
                        line.product_uom_id.id, product_qty,
                        uom_arba_with_code.id)

                if not line.product_id.arba_code:
                    raise UserError(_(
                        'No arba code for product "%s" (Id: %s)') % (
                        line.product_id.name, line.product_id.id))

                REMITOS_PRODUCTOS.append([
                    # TIPO_REGISTRO: 03
                    '03',

                    # CODIGO_UNICO_PRODUCTO
                    # nomenclador COT (Transporte de Bienes)
                    line.product_id.arba_code,

                    # RENTAS_CODIGO_UNIDAD_MEDIDA: ver tabla unidades de medida
                    uom_arba_with_code.arba_code,

                    # CANTIDAD: 13 enteros y 2 decimales (no incluir coma
                    # ni punto), ej 200 un -> 20000
                    str(int(round(product_qty * 100.0)))[-15:],

                    # PROPIO_CODIGO_PRODUCTO: máx. 25 caracteres
                    (line.product_id.default_code or '')[:25],

                    # PROPIO_DESCRIPCION_PRODUCTO: máx. 40 caracteres
                    (line.product_id.name)[:40],

                    # PROPIO_DESCRIPCION_UNIDAD_MEDIDA: máx. 20 caracteres
                    (uom_arba_with_code.name)[:20],

                    # CANTIDAD_AJUSTADA: 13 enteros y 2 decimales (no incluir
                    # coma ni punto), ej 200 un -> 20000 (en los que vi mandan
                    # lo mismo)
                    str(int(round(product_qty * 100.0)))[-15:],
                ])

        content = ''
        for line in [HEADER] + REMITOS_PRODUCTOS + [FOOTER]:
            content += '%s\r\n' % ('|'.join(line))
        #filename = 'TB_30712007288_001001_20190625_000031.txt'
        return (content, filename)

    @api.multi
    def do_pyafipws_presentar_remito(
            self, datetime_out, tipo_recorrido, carrier_partner,
            patente_vehiculo, patente_acomplado, prod_no_term_dev, importe):
        self.ensure_one()

        COT = self.company_id.arba_cot_connect()

        content, filename = self.get_arba_file_data(
            datetime_out, tipo_recorrido, carrier_partner,
            patente_vehiculo, patente_acomplado,
            prod_no_term_dev, importe)

        # NO podemos usar tmp porque agrega un sufijo distinto y arba exije
        # que sea tal cual el nombre del archivo
        # with tempfile.NamedTemporaryFile(
        #         prefix=filename, suffix='.txt') as file:
        #     file.write(content.encode('utf-8'))
        #     COT.PresentarRemito(file.name, testing="")

        parm_filename = str(filename)
        filename = '/tmp/%s' % filename
        file = open(filename, 'w+b')
        file.write(content.encode('utf-8'))
        file.close()
        #raise ValidationError('%s %s'%(filename,content))
        filename = str(filename)
        _logger.info('Presentando COT con archivo %s' % filename)
        COT.PresentarRemito(filename, testing=filename)
        raise ValidationError('Resultado COT %s'%COT.NumeroComprobante)
        #os.remove(filename)

        if COT.Excepcion:
            msg = _('Error al presentar remito:\n* %s') % COT.Excepcion
            _logger.warning(msg)
            raise UserError(msg)
        # no seria necesairio porque iteramos mas abajo
        # elif COT.CodigoError:
        #     msg = _(
        #         "Error al presentar remito:\n"
        #         "* MensajeError: %s\n"
        #         "* TipoError: %s\n"
        #         "* CodigoError: %s\n") % (
        #             COT.MensajeError, COT.TipoError, COT.CodigoError)
        #     _logger.warning(msg)
        #     raise UserError(msg)

        errors = []
        while COT.LeerErrorValidacion():
            errors.append((
                "* MensajeError: %s\n"
                "* TipoError: %s\n"
                "* CodigoError: %s\n") % (
                    COT.MensajeError, COT.TipoError, COT.CodigoError))

        if errors:
            raise UserError(_(
                "Error al presentar remito:\n%s") % '\n'.join(errors))
            # print "Error TipoError: %s" % COT.TipoError
            # print "Error CodigoError: %s" % COT.CodigoError
            # print "Error MensajeError: %s" % COT.MensajeError

        # TODO deberiamos tratar de usar este archivo y no generar el de arriba
        attachments = [(filename, content)]
        body = """
<p>
    Resultado solictud COT:
    <ul>
        <li>Número Comprobante: %s</li>
        <li>Codigo Integridad: %s</li>
        <li>Procesado: %s</li>
        <li>Número Único: %s</li>
    </ul>
</p>
""" % (COT.NumeroComprobante, COT.CodigoIntegridad,
            COT.Procesado, COT.NumeroUnico)

        self.write({
            'cot_numero_unico': COT.NumeroComprobante,
            'cot_numero_comprobante': COT.NumeroUnico,
        })
        self.message_post(
            body=body,
            subject=_('Remito Electrónico Solicitado'),
            attachments=attachments)
        # print 'COT.Excepcion', COT.Excepcion
        # if COT.Excepcion:
        #     raise UserError(
        # print 'COT.NumeroComprobante', COT.NumeroComprobante
        # print 'COT.CodigoIntegridad', COT.CodigoIntegridad
        # print 'COT.Procesado', COT.Procesado
        # print 'COT.NumeroUnico', COT.NumeroUnico

        return True
