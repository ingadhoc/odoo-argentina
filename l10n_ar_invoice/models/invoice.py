# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning
import openerp.addons.decimal_precision as dp


class account_invoice(models.Model):
    _inherit = "account.invoice"

    invoice_number = fields.Integer(
        compute='_get_invoice_number',
        string="Invoice Number",
        )
    point_of_sale = fields.Integer(
        compute='_get_invoice_number',
        string="Point Of Sale",
        )
    printed_amount_tax = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Tax'
        )
    printed_amount_untaxed = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Subtotal'
        )
    exempt_amount = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Exempt Amount'
        )
    vat_amount = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Vat Amount'
        )
    other_taxes_amount = fields.Float(
        compute="_get_taxes_and_prices",
        digits_compute=dp.get_precision('Account'),
        string='Other Taxes Amount'
        )
    printed_tax_ids = fields.One2many(
        compute="_get_taxes_and_prices",
        comodel_name='account.invoice.tax',
        string='Tax'
        )
    vat_tax_ids = fields.One2many(
        compute="_get_taxes_and_prices",
        comodel_name='account.invoice.tax',
        string='VAT Taxes'
        )
    not_vat_tax_ids = fields.One2many(
        compute="_get_taxes_and_prices",
        comodel_name='account.invoice.tax',
        string='Not VAT Taxes'
        )
    vat_discriminated = fields.Boolean(
        'Discriminate VAT?',
        compute="get_vat_discriminated",
        help="Discriminate VAT on Invoices?",
        )
    available_journal_document_class_ids = fields.Many2many(
        'account.journal.afip_document_class',
        compute='_get_available_journal_document_class',
        string='Available Journal Document Classes',
        )
    supplier_invoice_number = fields.Char(
        copy=False,
        )
    journal_document_class_id = fields.Many2one(
        'account.journal.afip_document_class',
        'Documents Type',
        readonly=True,
        states={'draft': [('readonly', False)]}
        )
    afip_document_class_id = fields.Many2one(
        'afip.document_class',
        related='journal_document_class_id.afip_document_class_id',
        string='Document Type',
        copy=False,
        readonly=True,
        store=True,
        )
    afip_document_number = fields.Char(
        string='Document Number',
        copy=False,
        readonly=True,
        )
    responsability_id = fields.Many2one(
        'afip.responsability',
        string='Responsability',
        readonly=True,
        copy=False,
        )
    formated_vat = fields.Char(
        string='Responsability',
        related='commercial_partner_id.formated_vat',
        )
    document_number = fields.Char(
        compute='_get_document_number',
        string='Document Number',
        readonly=True,
        )
    next_invoice_number = fields.Integer(
        related='journal_document_class_id.sequence_id.number_next_actual',
        string='Next Document Number',
        readonly=True
        )
    use_documents = fields.Boolean(
        related='journal_id.use_documents',
        string='Use Documents?',
        readonly=True
        )
    use_argentinian_localization = fields.Boolean(
        related='company_id.use_argentinian_localization',
        string='Use Argentinian Localization?',
        readonly=True,
        )
    afip_concept = fields.Selection(
        compute='_get_concept',
        selection=[('1', 'Consumible'),
                   ('2', 'Service'),
                   ('3', 'Mixed')],
        string="AFIP concept",
        )
    afip_service_start = fields.Date(
        string='Service Start Date'
        )
    afip_service_end = fields.Date(
        string='Service End Date'
        )

    @api.one
    @api.depends(
        'invoice_line',
        'invoice_line.product_id',
        'invoice_line.product_id.type',
        'use_argentinian_localization',
    )
    def _get_concept(self):
        afip_concept = False
        # If document has no connection then it is not electronic
        if self.use_argentinian_localization:
            product_types = set(
                [line.product_id.type for line in self.invoice_line if line.product_id])
            consumible = set(['consu', 'product'])
            service = set(['service'])
            mixed = set(['consu', 'service', 'product'])
            if product_types.issubset(mixed):
                afip_concept = '3'
            if product_types.issubset(service):
                afip_concept = '2'
            if product_types.issubset(consumible):
                afip_concept = '1'
        self.afip_concept = afip_concept

    @api.one
    def _get_taxes_and_prices(self):
        """ TODO, tal vez estos valores deban salir de la tabla de impuestos y
        y no del analisis de las lineas, usamos las lineas porque las lineas
        deben imprimir o no el monto con iva incluido o no, pero igualmente
        parece mas prolijo que todo esto empiece a venir de la tabla de
        impuestos. Dejariamos solo lo de las lineas para un tema de impresion
        que es algo mas simple y no incide en ningun lugar"""

        other_taxes_amount = sum(
            self.invoice_line.mapped('other_taxes_amount'))
        exempt_amount = sum(
            self.invoice_line.mapped('exempt_amount'))
        vat_taxes = self.tax_line.filtered(
            lambda r: r.tax_code_id.type == 'tax' and r.tax_code_id.tax == 'vat')
        not_vat_taxes = self.tax_line - vat_taxes
        vat_amount = sum(
            vat_taxes.mapped('tax_amount'))

        if self.vat_discriminated:
            printed_amount_untaxed = self.amount_untaxed
            printed_taxes = self.tax_line
        else:
            printed_amount_untaxed = self.amount_total
            printed_taxes = False

        self.printed_amount_untaxed = printed_amount_untaxed
        self.printed_tax_ids = printed_taxes
        self.printed_amount_tax = self.amount_total - printed_amount_untaxed
        self.vat_tax_ids = vat_taxes
        self.not_vat_tax_ids = not_vat_taxes
        self.vat_amount = vat_amount
        self.other_taxes_amount = other_taxes_amount
        self.exempt_amount = exempt_amount

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Supplier Invoice'),
            'out_refund': _('Refund'),
            'in_refund': _('Supplier Refund'),
        }
        result = []
        for inv in self:
            result.append((
                inv.id,
                "%s %s" % (
                    inv.document_number or TYPES[inv.type],
                    inv.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search(
                [('document_number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.one
    @api.depends(
        'journal_document_class_id',
        'company_id',
        )
    def get_vat_discriminated(self):
        vat_discriminated = False
        if self.afip_document_class_id.document_letter_id.vat_discriminated or self.company_id.invoice_vat_discrimination_default == 'discriminate_default':
            vat_discriminated = True
        self.vat_discriminated = vat_discriminated

    @api.one
    @api.depends('afip_document_number', 'number')
    def _get_invoice_number(self):
        """ Funcion que calcula numero de punto de venta y numero de factura
        a partir del document number. Es utilizado principalmente por el modulo
        de vat ledger citi
        """
        # TODO mejorar estp y almacenar punto de venta y numero de factura por separado
        # de hecho con esto hacer mas facil la carga de los comprobantes de compra
        str_number = self.afip_document_number or self.number or False
        if str_number and self.state not in ['draft', 'proforma', 'proforma2', 'cancel']:
            try:
                splited_number = str_number.split('-')
                invoice_number = int(splited_number.pop())
                point_of_sale = int(splited_number.pop())
            except:
                raise Warning(_(
                    'Could not get invoice number and point of sale for invoice id %i') % (
                        self.id))
            self.invoice_number = invoice_number
            self.point_of_sale = point_of_sale

    _sql_constraints = [
        ('number_supplier_invoice_number',
            'unique(supplier_invoice_number, partner_id, company_id)',
         'Supplier Invoice Number must be unique per Supplier and Company!'),
    ]

    @api.one
    @api.depends('journal_id', 'partner_id')
    def _get_available_journal_document_class(self):
        invoice_type = self.type
        document_class_ids = []
        document_class_id = False

        # Lo hicimos asi porque si no podria dar errores si en el context habia
        # un default de otra clase
        self.available_journal_document_class_ids = self.env[
            'account.journal.afip_document_class']
        if invoice_type in [
                'out_invoice', 'in_invoice', 'out_refund', 'in_refund']:
            operation_type = self.get_operation_type(invoice_type)

            if self.use_documents:
                # corremos con sudo porque da errores con usuario portal en algunos casos
                letter_ids = self.sudo().get_valid_document_letters(
                    self.partner_id.id, operation_type, self.company_id.id)
                domain = [
                    ('journal_id', '=', self.journal_id.id),
                    '|', ('afip_document_class_id.document_letter_id',
                          'in', letter_ids),
                    ('afip_document_class_id.document_letter_id', '=', False)]

                # If document_type in context we try to serch specific document
                document_type = self._context.get('document_type', False)
                if document_type:
                    document_classes = self.env[
                        'account.journal.afip_document_class'].search(
                        domain + [('afip_document_class_id.document_type', '=', document_type)])
                    if document_classes.ids:
                        document_class_id = document_classes.ids[0]

                # For domain, we search all documents
                document_classes = self.env[
                    'account.journal.afip_document_class'].search(domain)
                document_class_ids = document_classes.ids

                # If not specific document type found, we choose another one
                if not document_class_id and document_class_ids:
                    document_class_id = document_class_ids[0]
        self.available_journal_document_class_ids = document_class_ids
        self.journal_document_class_id = document_class_id

    @api.one
    @api.constrains(
        'journal_id', 'partner_id',
        'journal_document_class_id',
        )
    def _get_document_class(self):
        """ Como los campos responsability y journal document class no los
        queremos hacer funcion porque no queremos que sus valores cambien nunca
        y como con la funcion anterior solo se almacenan solo si se crea desde
        interfaz, hacemos este hack de constraint para computarlos si no estan
        computados"""
        if not self.journal_document_class_id and self.available_journal_document_class_ids:
            self.journal_document_class_id = self.available_journal_document_class_ids[0]

    @api.one
    @api.depends('afip_document_number', 'number')
    def _get_document_number(self):
        if self.afip_document_number and self.afip_document_class_id:
            document_number = (
                self.afip_document_class_id.doc_code_prefix or '') + self.afip_document_number
        else:
            document_number = self.number
        self.document_number = document_number

    @api.one
    @api.constrains('supplier_invoice_number', 'partner_id', 'company_id')
    def _check_reference(self):
        if self.type in ['out_invoice', 'out_refund'] and self.reference and self.state == 'open':
            domain = [('type', 'in', ('out_invoice', 'out_refund')),
                      # ('reference', '=', self.reference),
                      ('document_number', '=', self.document_number),
                      ('journal_document_class_id.afip_document_class_id', '=',
                       self.journal_document_class_id.afip_document_class_id.id),
                      ('company_id', '=', self.company_id.id),
                      ('id', '!=', self.id)]
            invoice_ids = self.search(domain)
            if invoice_ids:
                raise Warning(
                    _('Supplier Invoice Number must be unique per Supplier and Company!'))

    @api.multi
    def check_argentinian_invoice_taxes(self):
        # only check for argentinian localization companies
        argentinian_invoices = self.filtered('use_argentinian_localization')
        if not argentinian_invoices:
            return True

        # check invoice tax has code
        without_tax_code = self.env['account.invoice.tax'].search([
            ('invoice_id', 'in', argentinian_invoices.ids),
            ('tax_code_id', '=', False),
            ])
        if without_tax_code:
            raise Warning(_("You are using argentinian localization and there are some invoices with taxes that don't have tax code, tax code is required to generate this report. Invoies ids: %s" % without_tax_code.ids))

        # check codes has argentinian tax attributes configured
        tax_codes = argentinian_invoices.mapped('tax_line.tax_code_id')
        unconfigured_tax_codes = tax_codes.filtered(
            lambda r: not r.type or not r.tax or not r.application)
        if unconfigured_tax_codes:
            raise Warning(_("You are using argentinian localization and there are some tax codes that are not configured. Tax codes ids: %s" % unconfigured_tax_codes.ids))


        # checks for vat_discriminated invoices (A)
        # TODO verificar si la factura E por ejemplo, necesitan los mismo chequeos
        afip_exempt_codes = ['Z', 'X', 'E', 'N', 'C']
        for invoice in self:
            if not invoice.vat_discriminated:
                continue
            if invoice.exempt_amount and invoice.fiscal_position.afip_code not in afip_exempt_codes:
                raise Warning(_("If there you have choose a tax with 0, exempt or untaxed, you must choose a fiscal position with afip code in %s. Invoice id %i" % (
                    afip_exempt_codes, invoice.id)))
            # TODO tal vez habria que verificar que cada linea tiene un iva configurado
            if not invoice.vat_tax_ids:
                        raise Warning(_(
                            "Invoice id %i don't have any VAT tax." % invoice.id))

    @api.multi
    def action_number(self):
        self.check_argentinian_invoice_taxes()
        obj_sequence = self.env['ir.sequence']

        # We write document_number field with next invoice number by
        # document type
        for obj_inv in self:
            invtype = obj_inv.type
            # if we have a journal_document_class_id is beacuse we are in a
            # company that use this function
            # also if it has a reference number we use it (for example when
            # cancelling for modification)
            inv_vals = {'responsability_id': self.partner_id.commercial_partner_id.responsability_id.id}
            if obj_inv.journal_document_class_id and not obj_inv.afip_document_number:
                if invtype in ('out_invoice', 'out_refund'):
                    if not obj_inv.journal_document_class_id.sequence_id:
                        raise Warning(_('Error!. Please define sequence on the journal related documents to this invoice.'))
                    afip_document_number = obj_sequence.next_by_id(
                        obj_inv.journal_document_class_id.sequence_id.id)
                elif invtype in ('in_invoice', 'in_refund'):
                    afip_document_number = obj_inv.supplier_invoice_number
                inv_vals['afip_document_number'] = afip_document_number
                document_class_id = obj_inv.journal_document_class_id.afip_document_class_id.id
                obj_inv.move_id.write({
                    'document_class_id': document_class_id,
                    'afip_document_number': afip_document_number,
                    })
            obj_inv.write(inv_vals)
        res = super(account_invoice, self).action_number()
        return res

    @api.model
    def get_operation_type(self, invoice_type):
        if invoice_type in ['in_invoice', 'in_refund']:
            operation_type = 'purchase'
        elif invoice_type in ['out_invoice', 'out_refund']:
            operation_type = 'sale'
        else:
            operation_type = False
        return operation_type

    def get_valid_document_letters(
            self, cr, uid, partner_id, operation_type='sale',
            company_id=False, context=None):
        if context is None:
            context = {}

        document_letter_obj = self.pool.get('afip.document_letter')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        partner = self.pool.get('res.partner').browse(
            cr, uid, partner_id, context=context)

        if not partner_id or not company_id or not operation_type:
            return []

        partner = partner.commercial_partner_id

        if not company_id:
            company_id = context.get('company_id', user.company_id.id)
        company = self.pool.get('res.company').browse(
            cr, uid, company_id, context)

        if operation_type == 'sale':
            issuer_responsability_id = company.partner_id.responsability_id.id
            receptor_responsability_id = partner.responsability_id.id
        elif operation_type == 'purchase':
            issuer_responsability_id = partner.responsability_id.id
            receptor_responsability_id = company.partner_id.responsability_id.id
        else:
            raise except_orm(_('Operation Type Error'),
                             _('Operation Type Must be "Sale" or "Purchase"'))

        if not company.partner_id.responsability_id.id:
            raise except_orm(_('Your company has not setted any responsability'),
                             _('Please, set your company responsability in the company partner before continue.'))

        document_letter_ids = document_letter_obj.search(cr, uid, [(
            'issuer_ids', '=', issuer_responsability_id),
            ('receptor_ids', '=', receptor_responsability_id)],
            context=context)
        return document_letter_ids

    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        assert len(
            self) == 1, 'This option should only be used for a single id at a time.'
        template = self.env.ref(
            'l10n_ar_invoice.email_template_edi_invoice', False)
        compose_form = self.env.ref(
            'mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
