# -*- coding: utf-8 -*-
from openerp import osv, models, fields, api, _
from openerp.osv import fields as old_fields
from openerp.exceptions import except_orm, Warning
import openerp.addons.decimal_precision as dp


class account_invoice_line(models.Model):

    """
    En argentina como no se diferencian los impuestos en las facturas, excepto el IVA,
    agrego campos que ignoran el iva solamenta a la hora de imprimir los valores.
    """

    _inherit = "account.invoice.line"

    def _printed_prices(self, cr, uid, ids, name, args, context=None):
        res = {}
        tax_obj = self.pool['account.tax']
        cur_obj = self.pool.get('res.currency')

        for line in self.browse(cr, uid, ids, context=context):
            _round = (lambda x: cur_obj.round(
                cr, uid, line.invoice_id.currency_id, x)) if line.invoice_id else (lambda x: x)
            quantity = line.quantity
            discount = line.discount
            printed_price_unit = line.price_unit
            printed_price_net = line.price_unit * \
                (1 - (discount or 0.0) / 100.0)
            printed_price_subtotal = printed_price_net * quantity

            not_vat_taxes = [
                x for x in line.invoice_line_tax_id if x.tax_code_id.parent_id.name != 'IVA']
            taxes = tax_obj.compute_all(cr, uid,
                                        not_vat_taxes, printed_price_net, 1,
                                        product=line.product_id,
                                        partner=line.invoice_id.partner_id)
            other_taxes_amount = _round(
                taxes['total_included']) - _round(taxes['total'])

            # TODO: tal vez mejorar esto de que se buscan los iva por el que tiene padre llamado "IVA"
            # Antes habiamos agregado un vampo vat_tax en los code pero el tema
            # es que tambien hay que agregarlo en el template de los tax code y
            # en los planes de cuenta, resulta medio engorroso
            vat_taxes = [
                x for x in line.invoice_line_tax_id if x.tax_code_id.parent_id.name == 'IVA']
            taxes = tax_obj.compute_all(cr, uid,
                                        vat_taxes, printed_price_net, 1,
                                        product=line.product_id,
                                        partner=line.invoice_id.partner_id)
            vat_amount = _round(
                taxes['total_included']) - _round(taxes['total'])

            exempt_amount = 0.0
            if not vat_taxes:
                exempt_amount = _round(taxes['total_included'])

            # For document that not discriminate we include the prices
            if not line.invoice_id.vat_discriminated:
                printed_price_unit = _round(
                    taxes['total_included'] * (1 + (discount or 0.0) / 100.0))
                printed_price_net = _round(taxes['total_included'])
                printed_price_subtotal = _round(
                    taxes['total_included'] * quantity)

            res[line.id] = {
                'printed_price_unit': printed_price_unit,
                'printed_price_net': printed_price_net,
                'printed_price_subtotal': printed_price_subtotal,
                'vat_amount': vat_amount * quantity,
                'other_taxes_amount': other_taxes_amount * quantity,
                'exempt_amount': exempt_amount * quantity,
            }
        return res

    _columns = {
        'printed_price_unit': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Unit Price', multi='printed',),
        'printed_price_net': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Net Price', multi='printed'),
        'printed_price_subtotal': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Subtotal', multi='printed'),
        'vat_amount': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Vat Amount', multi='printed'),
        'other_taxes_amount': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Other Taxes Amount', multi='printed'),
        'exempt_amount': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Exempt Amount', multi='printed'),
    }


class account_invoice(models.Model):
    _inherit = "account.invoice"

    def _printed_prices(self, cr, uid, ids, name, args, context=None):
        res = {}

        for invoice in self.browse(cr, uid, ids, context=context):
            printed_amount_untaxed = invoice.amount_untaxed
            printed_tax_ids = [x.id for x in invoice.tax_line]

            # vat_amount = sum(
            #     line.vat_amount for line in invoice.invoice_line)
            # Por errores de redonde cambiamos la forma anterior por esta nueva
            vat_amount = sum([
                x.tax_amount for x in invoice.tax_line if x.tax_code_id.parent_id.name == 'IVA'])

            other_taxes_amount = sum(
                line.other_taxes_amount for line in invoice.invoice_line)
            exempt_amount = sum(
                line.exempt_amount for line in invoice.invoice_line)
            vat_tax_ids = [
                x.id for x in invoice.tax_line if x.tax_code_id.parent_id.name == 'IVA']

            if not invoice.vat_discriminated:
                printed_amount_untaxed = sum(
                    line.printed_price_subtotal for line in invoice.invoice_line)
                printed_tax_ids = [
                    x.id for x in invoice.tax_line if x.tax_code_id.parent_id.name != 'IVA']
            res[invoice.id] = {
                'printed_amount_untaxed': printed_amount_untaxed,
                'printed_tax_ids': printed_tax_ids,
                'printed_amount_tax': invoice.amount_total - printed_amount_untaxed,
                'vat_tax_ids': vat_tax_ids,
                'vat_amount': vat_amount,
                'other_taxes_amount': other_taxes_amount,
                'exempt_amount': exempt_amount,
            }
        return res

    _columns = {
        'printed_amount_tax': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Tax', multi='printed',),
        'printed_amount_untaxed': old_fields.function(
            _printed_prices,
            type='float', digits_compute=dp.get_precision('Account'),
            string='Subtotal', multi='printed',),
        'printed_tax_ids': old_fields.function(
            _printed_prices,
            type='one2many', relation='account.invoice.tax', string='Tax',
            multi='printed'),
        'exempt_amount': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Exempt Amount', multi='printed'),
        'vat_tax_ids': old_fields.function(
            _printed_prices,
            type='one2many', relation='account.invoice.tax',
            string='VAT Taxes', multi='printed'),
        'vat_amount': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Vat Amount', multi='printed'),
        'other_taxes_amount': old_fields.function(
            _printed_prices, type='float',
            digits_compute=dp.get_precision('Account'),
            string='Other Taxes Amount', multi='printed')
    }

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
            result.append(
                (inv.id, "%s %s" % (inv.document_number or TYPES[inv.type], inv.name or '')))
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
                letter_ids = self.get_valid_document_letters(
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
    @api.depends(
        'afip_document_class_id',
        'afip_document_class_id.document_letter_id',
        'afip_document_class_id.document_letter_id.vat_discriminated',
        'company_id',
        'company_id.invoice_vat_discrimination_default',)
    def get_vat_discriminated(self):
        vat_discriminated = False
        if self.afip_document_class_id.document_letter_id.vat_discriminated or self.company_id.invoice_vat_discrimination_default == 'discriminate_default':
            vat_discriminated = True
        self.vat_discriminated = vat_discriminated

    vat_discriminated = fields.Boolean(
        'Discriminate VAT?',
        compute="get_vat_discriminated",
        store=True,
        readonly=False,
        help="Discriminate VAT on Quotations and Sale Orders?")

    available_journal_document_class_ids = fields.Many2many(
        'account.journal.afip_document_class',
        # TODO hay un warning cada vez que se crea una factura que dice:
        # No such field(s) in model account.invoice:available_journal_document_class_ids
        # la unica forma que encontre de sacarlo es agregando el store, lo dejo
        # por las dudas pero la idea es ver si la api se arregla, no hace falta
        # y podemos borrar esto
        # 'available_journal_class_invoice_rel',
        # 'invoice_id', 'journal_class_id',
        # store=True,
        compute='_get_available_journal_document_class',
        string='Available Journal Document Classes')
    supplier_invoice_number = fields.Char(
        copy=False)
    journal_document_class_id = fields.Many2one(
        'account.journal.afip_document_class',
        'Documents Type',
        compute="_get_available_journal_document_class",
        readonly=True,
        store=True,
        states={'draft': [('readonly', False)]})
    afip_document_class_id = fields.Many2one(
        'afip.document_class',
        related='journal_document_class_id.afip_document_class_id',
        string='Document Type',
        copy=False,
        readonly=True,
        store=True)
    afip_document_number = fields.Char(
        string='Document Number',
        copy=False,
        readonly=True,)
    responsability_id = fields.Many2one(
        'afip.responsability',
        string='Responsability',
        related='commercial_partner_id.responsability_id',
        store=True,
        )
    formated_vat = fields.Char(
        string='Responsability',
        related='commercial_partner_id.formated_vat',)

    @api.one
    @api.depends('afip_document_number', 'number')
    def _get_document_number(self):
        if self.afip_document_number and self.afip_document_class_id:
            document_number = (
                self.afip_document_class_id.doc_code_prefix or '') + self.afip_document_number
        else:
            document_number = self.number
        self.document_number = document_number

    document_number = fields.Char(
        compute='_get_document_number',
        string='Document Number',
        readonly=True,
        # store=True
    )
    next_invoice_number = fields.Integer(
        related='journal_document_class_id.sequence_id.number_next_actual',
        string='Next Document Number',
        readonly=True)
    use_documents = fields.Boolean(
        related='journal_id.use_documents',
        string='Use Documents?',
        readonly=True)

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

    _sql_constraints = [
        ('number_supplier_invoice_number',
            'unique(supplier_invoice_number, partner_id, company_id)',
         'Supplier Invoice Number must be unique per Supplier and Company!'),
    ]

    @api.multi
    def action_number(self):
        obj_sequence = self.env['ir.sequence']

        # We write document_number field with next invoice number by
        # document type
        for obj_inv in self:
            invtype = obj_inv.type
            # if we have a journal_document_class_id is beacuse we are in a
            # company that use this function
            # also if it has a reference number we use it (for example when
            # cancelling for modification)
            if obj_inv.journal_document_class_id and not obj_inv.afip_document_number:
                if invtype in ('out_invoice', 'out_refund'):
                    if not obj_inv.journal_document_class_id.sequence_id:
                        raise osv.except_osv(_('Error!'), _(
                            'Please define sequence on the journal related documents to this invoice.'))
                    afip_document_number = obj_sequence.next_by_id(
                        obj_inv.journal_document_class_id.sequence_id.id)
                elif invtype in ('in_invoice', 'in_refund'):
                    afip_document_number = obj_inv.supplier_invoice_number
                obj_inv.write({'afip_document_number': afip_document_number})
                document_class_id = obj_inv.journal_document_class_id.afip_document_class_id.id
                obj_inv.move_id.write(
                    {'document_class_id': document_class_id,
                     'afip_document_number': self.afip_document_number})
        res = super(account_invoice, self).action_number()

        return res

    def get_operation_type(self, cr, uid, invoice_type, context=None):
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
            'issuer_ids', 'in', issuer_responsability_id),
            ('receptor_ids', 'in', receptor_responsability_id)],
            context=context)
        return document_letter_ids
