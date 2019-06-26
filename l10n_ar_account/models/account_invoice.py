##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import re
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    afip_invoice_concepts = [
        ('1', 'Producto / Exportación definitiva de bienes'),
        ('2', 'Servicios'),
        ('3', 'Productos y Servicios'),
        ('4', '4-Otros (exportación)'),
    ]

    main_id_number = fields.Char(
        related='commercial_partner_id.main_id_number',
        readonly=True,
    )
    state_id = fields.Many2one(
        # related='commercial_partner_id.state_id',
        # al final lo hacemos por contacto (y no commercial) para poder usar
        # direcciones distintas
        related='partner_id.state_id',
        store=True,
        readonly=True,
        auto_join=True,
    )
    # IMPORANTE: si llegamos a implementar el campo computado no usar
    # cotizacion de la moneda ya que esta puede cambiar y ademas, si facturamos
    # algo futuro y no existe cotizacion, se usa la de hoy y luego al agregar
    # la cotizacion este dato va a cambiar
    # TODO: depreciar este campo y la funcion que lo setea, lo dejamos por
    # ahora para que no se borre esta columna que ya esta calculada, pero si
    # todo va bien con el nuevo computado, lo vamos a borrar directamente
    currency_rate = fields.Float(
        string='Currency Rate',
        copy=False,
        digits=(16, 4),
        # TODO make it editable, we have to change move create method
        readonly=True,
    )
    computed_currency_rate = fields.Float(
        string='Currency Rate',
        digits=(16, 4),
        compute='_compute_currency_rate',
    )
    document_letter_id = fields.Many2one(
        related='document_type_id.document_letter_id',
        readonly=True,
    )
    document_letter_name = fields.Char(
        related='document_letter_id.name',
        readonly=True,
    )
    taxes_included = fields.Boolean(
        related='document_letter_id.taxes_included',
        readonly=True,
    )
    # mostly used on reports
    afip_responsability_type_id = fields.Many2one(
        'afip.responsability.type',
        string='AFIP Responsability Type',
        readonly=True,
        help='Responsability type from journal entry where it is stored and '
        'it nevers change',
        related='move_id.afip_responsability_type_id',
        index=True,
        auto_join=True,
    )
    invoice_number = fields.Integer(
        compute='_compute_invoice_number',
        string="Invoice Number",
    )
    point_of_sale_number = fields.Integer(
        compute='_compute_invoice_number',
        string="Point Of Sale",
    )
# impuestos e importes de impuestos
    # todos los impuestos tipo iva (es un concepto mas bien interno)
    vat_tax_ids = fields.One2many(
        compute="_compute_argentina_amounts",
        comodel_name='account.invoice.tax',
        string='VAT Taxes'
    )
    # todos los impuestos iva que componene base imponible (no se incluyen 0,
    # 1, 2 que no son impuesto en si)
    vat_taxable_ids = fields.One2many(
        compute="_compute_argentina_amounts",
        comodel_name='account.invoice.tax',
        string='VAT Taxes'
    )
    # todos los impuestos menos los tipo iva vat_tax_ids
    not_vat_tax_ids = fields.One2many(
        compute="_compute_argentina_amounts",
        comodel_name='account.invoice.tax',
        string='Not VAT Taxes'
    )
    # suma de base para todos los impuestos tipo iva
    # TODO revisar si se usa y si no borrar
    vat_base_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
        string='VAT Base Amount'
    )
    # base imponible (no se incluyen no corresponde, exento y no gravado)
    vat_taxable_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
        string='VAT Taxable Amount'
    )
    # base iva exento
    vat_exempt_base_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
        string='VAT Exempt Base Amount'
    )
    # base iva no gravado
    vat_untaxed_base_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
        string='VAT Untaxed Base Amount'
    )
    # importe de iva
    vat_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
        string='VAT Amount'
    )
    # importe de otros impuestos
    other_taxes_amount = fields.Monetary(
        compute="_compute_argentina_amounts",
        string='Other Taxes Amount'
    )
    afip_incoterm_id = fields.Many2one(
        'afip.incoterm',
        'Incoterm',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    point_of_sale_type = fields.Selection(
        related='journal_id.point_of_sale_type',
        readonly=True,
    )
    # estos campos los agregamos en este modulo pero en realidad los usa FE
    # pero entendemos que podrian ser necesarios para otros tipos, por ahora
    # solo lo vamos a hacer requerido si el punto de venta es del tipo
    # electronico
    # TODO mejorar, este concepto deberia quedar fijo y no poder modificarse
    # una vez validada, cosa que pasaria por ej si cambias el producto
    afip_concept = fields.Selection(
        compute='_compute_concept',
        inverse='_inverse_concept',
        # store=True,
        selection=afip_invoice_concepts,
        string="AFIP concept",
        help="Se sugiere un concepto en función a la configuración de los "
        "productos (tipo servicio, consumible o almacenable) pero se puede "
        "cambiar este valor si lo requiere.",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    # la idea es incorporar la posibilidad de forzar otro concepto distinto
    # al sugerido, para no complicarla y ser compatible hacia atras de manera
    # simple, agregamos este otro campo
    force_afip_concept = fields.Selection(
        selection=afip_invoice_concepts,
        string="AFIP concept",
        readonly=True,
    )
    afip_service_start = fields.Date(
        string='Service Start Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    afip_service_end = fields.Date(
        string='Service End Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    @api.multi
    def _compute_argentina_amounts(self):
        """
        """
        for rec in self:
            vat_taxes = rec.tax_line_ids.filtered(
                lambda r: (
                    r.tax_id.tax_group_id.type == 'tax' and
                    r.tax_id.tax_group_id.tax == 'vat'))
            # we add and "r.base" because only if a there is a base amount it
            # is considered taxable, this is used for eg to validate invoices
            # on afip
            vat_taxables = vat_taxes.filtered(
                lambda r: (
                    r.tax_id.tax_group_id.afip_code not in
                    [0, 1, 2]) and r.base)

            vat_amount = sum(vat_taxes.mapped('amount'))
            rec.vat_tax_ids = vat_taxes
            rec.vat_taxable_ids = vat_taxables
            rec.vat_amount = vat_amount
            # rec.vat_taxable_amount = sum(vat_taxables.mapped('base_amount'))
            rec.vat_taxable_amount = sum(vat_taxables.mapped('base'))
            # rec.vat_base_amount = sum(vat_taxes.mapped('base_amount'))
            rec.vat_base_amount = sum(vat_taxes.mapped('base'))

            # vat exempt values
            # exempt taxes are the ones with code 2
            vat_exempt_taxes = rec.tax_line_ids.filtered(
                lambda r: (
                    r.tax_id.tax_group_id.type == 'tax' and
                    r.tax_id.tax_group_id.tax == 'vat' and
                    r.tax_id.tax_group_id.afip_code == 2))
            rec.vat_exempt_base_amount = sum(
                vat_exempt_taxes.mapped('base'))
            # rec.vat_exempt_base_amount = sum(
            #     vat_exempt_taxes.mapped('base_amount'))

            # vat_untaxed_base_amount values (no gravado)
            # vat exempt taxes are the ones with code 1
            vat_untaxed_taxes = rec.tax_line_ids.filtered(
                lambda r: (
                    r.tax_id.tax_group_id.type == 'tax' and
                    r.tax_id.tax_group_id.tax == 'vat' and
                    r.tax_id.tax_group_id.afip_code == 1))
            rec.vat_untaxed_base_amount = sum(
                vat_untaxed_taxes.mapped('base'))
            # rec.vat_untaxed_base_amount = sum(
            #     vat_untaxed_taxes.mapped('base_amount'))

            # other taxes values
            not_vat_taxes = rec.tax_line_ids - vat_taxes
            other_taxes_amount = sum(not_vat_taxes.mapped('amount'))
            rec.not_vat_tax_ids = not_vat_taxes
            rec.other_taxes_amount = other_taxes_amount

    @api.multi
    @api.depends('document_number', 'number')
    def _compute_invoice_number(self):
        """ Funcion que calcula numero de punto de venta y numero de factura
        a partir del document number. Es utilizado principalmente por el modulo
        de vat ledger citi
        """
        # TODO mejorar estp y almacenar punto de venta y numero de factura por
        # separado, de hecho con esto hacer mas facil la carga de los
        # comprobantes de compra

        # decidimos obtener esto solamente para comprobantes con doc number
        for rec in self:
            str_number = rec.document_number or False
            if str_number:
                if rec.document_type_id.code in ['33', '99', '331', '332']:
                    point_of_sale = '0'
                    # leave only numbers and convert to integer
                    # otherwise use date as a number
                    if re.search(r'\d', str_number):
                        invoice_number = str_number
                    else:
                        invoice_number = rec.date_invoice
                # despachos de importacion
                elif rec.document_type_id.code == '66':
                    point_of_sale = '0'
                    invoice_number = '0'
                elif "-" in str_number:
                    splited_number = str_number.split('-')
                    invoice_number = splited_number.pop()
                    point_of_sale = splited_number.pop()
                elif "-" not in str_number and len(str_number) == 12:
                    point_of_sale = str_number[:4]
                    invoice_number = str_number[-8:]
                else:
                    raise ValidationError(_(
                        'Could not get invoice number and point of sale for '
                        'Invoice [%i] %s') % (rec.id, rec.display_name))
                rec.invoice_number = int(
                    re.sub("[^0-9]", "", invoice_number))
                rec.point_of_sale_number = int(
                    re.sub("[^0-9]", "", point_of_sale))

    @api.multi
    def _inverse_concept(self):
        for rec in self:
            if rec._get_concept() == rec.afip_concept:
                rec.force_afip_concept = False
            else:
                rec.force_afip_concept = rec.afip_concept

    @api.multi
    def _get_concept(self):
        """
        Metodo para obtener el concepto en funcion a los productos de una
        factura, luego es utilizado por los metodos inverse y compute del campo
        afip_concept
        """
        self.ensure_one()
        invoice_lines = self.invoice_line_ids
        product_types = set([
            x.product_id.type for x in invoice_lines
            if x.product_id])
        consumible = set(['consu', 'product'])
        service = set(['service'])
        mixed = set(['consu', 'service', 'product'])
        # default value "product"
        afip_concept = '1'
        if product_types.issubset(mixed):
            afip_concept = '3'
        if product_types.issubset(service):
            afip_concept = '2'
        if product_types.issubset(consumible):
            afip_concept = '1'
        if self.document_type_id.code in ['19', '20', '21']:
            # en realidad para expo no se puede informar productos y servicios
            # en mismo comprobante, este otros no sabemos bien que significa,
            # si hay mezcla de productos y servicios lo dejamos como producto
            # ya que es más seguro al exigir que el usuario agregue el Incoterm
            if afip_concept == '3':
                afip_concept = '1'
        return afip_concept

    @api.multi
    @api.depends(
        'invoice_line_ids',
        'invoice_line_ids.product_id',
        'invoice_line_ids.product_id.type',
        'localization',
        'force_afip_concept',
    )
    def _compute_concept(self):
        for rec in self:
            afip_concept = False
            if rec.point_of_sale_type in ['online', 'electronic']:
                if rec.force_afip_concept:
                    afip_concept = rec.force_afip_concept
                else:
                    afip_concept = rec._get_concept()
            rec.afip_concept = afip_concept

    # TODO al final lo re implementamos solo para poder previsualizar
    # cual va a ser la cotizacion, es medio feo pero lo hacemos asi para tener
    # solucion rapida, deberiamos hacer algo mas definitivo
    # TODO borrar o implementar. Al final usamos el currency rate que
    # almacenamos porque es muy inexacto calcularlo ya que se pierde
    # información y segun el importe, al mismo cambio, podriamos tener
    # distintos valores de cambio
    @api.depends('currency_id', 'company_id', 'date_invoice')
    def _compute_currency_rate(self):
        for rec in self:
            if rec.currency_id and rec.company_id and (
                    rec.currency_id != rec.company_id.currency_id):
                # rec.computed_currency_rate = abs(
                #     rec.amount_total_company_signed / rec.amount_total)
                currency = rec.currency_id.with_context(
                    company_id=rec.company_id.id,
                    date=rec.date_invoice or fields.Date.context_today(rec))
                rec.computed_currency_rate = currency.compute(
                    1., self.company_id.currency_id, round=False)
            else:
                rec.computed_currency_rate = 1.0

    @api.multi
    def get_localization_invoice_vals(self):
        self.ensure_one()
        # TODO depreciar esta funcion y convertir a currency_rate campo
        # calculado que la calcule en funcion a los datos del move
        if self.localization == 'argentina':
            if self.company_id.currency_id == self.currency_id:
                currency_rate = 1.0
            else:
                currency = self.currency_id.with_context(
                    company_id=self.company_id.id,
                    date=self.date_invoice or fields.Date.context_today(self))
                currency_rate = currency.compute(
                    1., self.company_id.currency_id, round=False)
            return {
                'currency_rate': currency_rate,
            }
        else:
            return super(
                AccountInvoice, self).get_localization_invoice_vals()

    @api.model
    def _get_available_journal_document_types(
            self, journal, invoice_type, partner):
        """
        This function search for available document types regarding:
        * Journal
        * Partner
        * Company
        * Documents configuration
        If needed, we can make this funcion inheritable and customizable per
        localization
        """
        if journal.localization != 'argentina':
            return super(
                AccountInvoice, self)._get_available_journal_document_types(
                    journal, invoice_type, partner)

        commercial_partner = partner.commercial_partner_id

        journal_document_types = journal_document_type = self.env[
            'account.journal.document.type']

        if invoice_type in [
                'out_invoice', 'in_invoice', 'out_refund', 'in_refund']:

            if journal.use_documents:
                letters = journal.get_journal_letter(
                    counterpart_partner=commercial_partner)

                domain = [
                    ('journal_id', '=', journal.id),
                    '|',
                    ('document_type_id.document_letter_id', 'in', letters.ids),
                    ('document_type_id.document_letter_id', '=', False),
                ]

                # if invoice_type is refund, only credit notes
                if invoice_type in ['out_refund', 'in_refund']:
                    domain = [
                        ('document_type_id.internal_type',
                            # '=', 'credit_note')]
                            # TODO, check if we need to add tickets and others
                            # also
                            'in', ['credit_note', 'in_document'])] + domain
                # else, none credit notes
                else:
                    # usamos not in porque != no funciona bien, no muestra los
                    # que tienen internal type = False
                    domain = [
                        ('document_type_id.internal_type',
                            'not in', ['credit_note'])] + domain

                # If internal_type in context we try to serch specific document
                # for eg used on debit notes
                internal_type = self._context.get('internal_type', False)
                if internal_type:
                    journal_document_type = journal_document_type.search(
                        [('document_type_id.internal_type',
                            '=', internal_type)] + domain, limit=1)
                # For domain, we search all documents
                journal_document_types = journal_document_types.search(domain)

                # If not specific document type found, we choose another one
                if not journal_document_type and journal_document_types:
                    journal_document_type = journal_document_types[0]

        if invoice_type == 'in_invoice':
            other_document_types = (commercial_partner.other_document_type_ids)

            domain = [
                ('journal_id', '=', journal.id),
                ('document_type_id',
                    'in', other_document_types.ids),
            ]
            other_journal_document_types = self.env[
                'account.journal.document.type'].search(domain)

            journal_document_types += other_journal_document_types
            # if we have some document sepecific for the partner, we choose it
            if other_journal_document_types:
                journal_document_type = other_journal_document_types[0]

        return {
            'available_journal_document_types': journal_document_types,
            'journal_document_type': journal_document_type,
        }

    @api.multi
    def action_move_create(self):
        """
        We add currency rate on move creation so it can be used by electronic
        invoice later on action_number
        """
        self.check_argentinian_invoice_taxes()
        return super(AccountInvoice, self).action_move_create()

    @api.multi
    def check_argentinian_invoice_taxes(self):
        """
        We make theis function to be used as a constraint but also to be called
        from other models like vat citi
        """
        # only check for argentinian localization companies
        _logger.info('Running checks related to argentinian documents')

        # we consider argentinian invoices the ones from companies with
        # localization localization and that belongs to a journal with
        # use_documents
        argentinian_invoices = self.filtered(
            lambda r: (
                r.localization == 'argentina' and r.use_documents))
        if not argentinian_invoices:
            return True

        # we check that there is one and only one vat tax. We check upon
        # validation to avoid errors on invoice creations from other menus
        # and for performance
        for inv_line in argentinian_invoices.filtered(
                lambda x: x.company_id.company_requires_vat).mapped(
                    'invoice_line_ids'):
            vat_taxes = inv_line.invoice_line_tax_ids.filtered(
                lambda x:
                x.tax_group_id.tax == 'vat' and x.tax_group_id.type == 'tax')
            if len(vat_taxes) != 1:
                raise ValidationError(_(
                    'Debe haber un y solo un impuesto de IVA por línea. '
                    'Verificar líneas con producto "%s"' % (
                        inv_line.product_id.name)))

        # check partner has responsability so it will be assigned on invoice
        # validate
        without_responsability = argentinian_invoices.filtered(
            lambda x: not x.commercial_partner_id.afip_responsability_type_id)
        if without_responsability:
            raise ValidationError(_(
                'The following invoices has a partner without AFIP '
                'responsability:\r\n\r\n'
                '%s') % ('\r\n'.join(
                    ['[%i] %s' % (i.id, i.display_name)
                        for i in without_responsability])))

        # we check all invoice tax lines has tax_id related
        # we exclude exempt vats and untaxed (no gravados)
        wihtout_tax_id = argentinian_invoices.mapped('tax_line_ids').filtered(
            lambda r: not r.tax_id)
        if wihtout_tax_id:
            raise ValidationError(_(
                "Some Invoice Tax Lines don't have a tax_id asociated, please "
                "correct them or try to refresh invoice. Tax lines: %s") % (
                ', '.join(wihtout_tax_id.mapped('name'))))

        # check codes has argentinian tax attributes configured
        tax_groups = argentinian_invoices.mapped(
            'tax_line_ids.tax_id.tax_group_id')
        unconfigured_tax_groups = tax_groups.filtered(
            lambda r: not r.type or not r.tax or not r.application)
        if unconfigured_tax_groups:
            raise ValidationError(_(
                "You are using argentinian localization and there are some tax"
                " groups that are not configured. Tax Groups (id): %s" % (
                    ', '.join(unconfigured_tax_groups.mapped(
                        lambda x: '%s (%s)' % (x.name, x.id))))))

        # for invoice in argentinian_invoices:
        #     # TODO usar round
        #     # TODO tal vez debamos usar esto para un chequeo de suma de
        #     # importes y demas, tener en cuenta caso de importaciones
        #     # tal como esta este chequeo da error si se agregan impuestos
        #     # manuales
        #     if abs(invoice.vat_base_amount - invoice.amount_untaxed) > 0.1:
        #         raise ValidationError(_(
        #             "Invoice with ID %i has some lines without vat Tax ") % (
        #                 invoice.id))

        # verificamos facturas de compra que deben reportar cuit y no lo tienen
        # configurado
        without_cuit = argentinian_invoices.filtered(
            lambda x: x.type in ['in_invoice', 'in_refund'] and
            x.document_type_id.purchase_cuit_required and
            not x.commercial_partner_id.cuit)
        if without_cuit:
            raise ValidationError(_(
                'Las siguientes partners no tienen configurado CUIT: %s') % (
                    ', '.join(
                        without_cuit.mapped('commercial_partner_id.name'))
            ))

        # facturas que no debería tener ningún iva y tienen
        not_zero_alicuot = argentinian_invoices.filtered(
            lambda x: x.type in ['in_invoice', 'in_refund'] and
            x.document_type_id.purchase_alicuots == 'zero' and
            any([t.tax_id.tax_group_id.afip_code != 0 for t in x.vat_tax_ids]))
        if not_zero_alicuot:
            raise ValidationError(_(
                'Las siguientes facturas tienen configurados IVA incorrecto. '
                'Debe utilizar IVA no corresponde.\n*Facturas: %s') % (
                    ', '.join(not_zero_alicuot.mapped('display_name'))
            ))

        # facturas que debería tener iva y tienen no corresponde
        zero_alicuot = argentinian_invoices.filtered(
            lambda x: x.type in ['in_invoice', 'in_refund'] and
            x.document_type_id.purchase_alicuots == 'not_zero' and
            any([t.tax_id.tax_group_id.afip_code == 0 for t in x.vat_tax_ids]))
        if zero_alicuot:
            raise ValidationError(_(
                'Las siguientes facturas tienen IVA no corresponde pero debe '
                'seleccionar una alícuota correcta (No gravado, Exento, Cero, '
                '10,5, etc).\n*Facturas: %s') % (
                    ', '.join(zero_alicuot.mapped('display_name'))
            ))

        # Check except vat invoice
        afip_exempt_codes = ['Z', 'X', 'E', 'N', 'C']
        for invoice in argentinian_invoices:
            special_vat_taxes = invoice.tax_line_ids.filtered(
                lambda r: r.tax_id.tax_group_id.afip_code in [1, 2, 3])
            if (
                    special_vat_taxes and
                    invoice.fiscal_position_id.afip_code
                    not in afip_exempt_codes):
                raise ValidationError(_(
                    "If you have choose a 0, exempt or untaxed 'tax', or "
                    "you must choose a fiscal position with afip code in %s.\n"
                    "* Invoice [%i] %s") % (
                        afip_exempt_codes,
                        invoice.id,
                        invoice.display_name))

            # esto es, por eje, si hay un producto con 100% de descuento para
            # única alicuota, entonces el impuesto liquidado da cero y se
            # obliga reportar con alicuota 0, entonces se exige tmb cod de op.
            # esta restriccion no es de FE si no de aplicativo citi
            vat_taxes = invoice.tax_line_ids.filtered(
                lambda x: x.tax_id.tax_group_id.afip_code in [
                    4, 5, 6, 8, 9])
            zero_vat_lines = vat_taxes and all(
                x.currency_id.is_zero(x.amount) for x in vat_taxes)
            if (
                    zero_vat_lines and
                    invoice.fiscal_position_id.afip_code
                    not in afip_exempt_codes):
                raise ValidationError(_(
                    "Si hay líneas con IVA declarado 0, entonces debe elegir "
                    "una posición fiscal con código de afip '%s'.\n"
                    "* Invoice [%i] %s") % (
                        afip_exempt_codes,
                        invoice.id,
                        invoice.display_name))

    # TODO sacamos esto porque no era muy lindo y daba algunos errores con
    # el account_fix, hicimos que los datos demo hagan el compute tax
    # habria que ver una mejor forma de hacerlo para que tambien ande bien si
    # se importa desde interfaz
    # If we import or get demo data
    # tax_id is not loaded on tax lines, we couldn't find the error
    # so we add this to fix it
    # @api.one
    # @api.constrains('invoice_line_ids')
    # def update_taxes_fix(self):
    #     context = dict(self._context)
    #     if context.get('constraint_update_taxes'):
    #         return True
    #     self.with_context(constraint_update_taxes=True).compute_taxes()

    # we add fiscal position with fp method instead of directly from partner

    @api.constrains('date_invoice')
    def set_date_afip(self):
        for rec in self.filtered('date_invoice'):
            date_invoice = fields.Datetime.from_string(rec.date_invoice)
            vals = {}
            if not rec.afip_service_start:
                vals['afip_service_start'] = (
                    date_invoice + relativedelta(day=1))
            if not rec.afip_service_end:
                vals['afip_service_end'] = date_invoice + \
                    relativedelta(day=1, days=-1, months=+1)
            if vals:
                rec.write(vals)
