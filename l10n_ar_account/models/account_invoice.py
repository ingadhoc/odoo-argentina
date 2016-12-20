# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import UserError
from dateutil.relativedelta import relativedelta
import re
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    currency_rate = fields.Float(
        string='Currency Rate',
        copy=False,
        digits=(16, 4),
        # TODO make it editable, we have to change move create method
        readonly=True,
    )
    document_letter_id = fields.Many2one(
        related='document_type_id.document_letter_id',
    )
    document_letter_name = fields.Char(
        related='document_letter_id.name'
    )
    taxes_included = fields.Boolean(
        related='document_letter_id.taxes_included',
    )
    afip_responsability_type_id = fields.Many2one(
        'afip.responsability.type',
        string='AFIP Responsability Type',
        readonly=True,
        copy=False,
    )
    invoice_number = fields.Integer(
        compute='_get_invoice_number',
        string="Invoice Number",
    )
    point_of_sale_number = fields.Integer(
        compute='_get_invoice_number',
        string="Point Of Sale",
    )
# impuestos e importes de impuestos
    # todos los impuestos tipo iva (es un concepto mas bien interno)
    vat_tax_ids = fields.One2many(
        compute="_get_argentina_amounts",
        comodel_name='account.invoice.tax',
        string='VAT Taxes'
    )
    # todos los impuestos iva que componene base imponible (no se incluyen 0,
    # 1, 2 que no son impuesto en si)
    vat_taxable_ids = fields.One2many(
        compute="_get_argentina_amounts",
        comodel_name='account.invoice.tax',
        string='VAT Taxes'
    )
    # todos los impuestos menos los tipo iva vat_tax_ids
    not_vat_tax_ids = fields.One2many(
        compute="_get_argentina_amounts",
        comodel_name='account.invoice.tax',
        string='Not VAT Taxes'
    )
    # suma de base para todos los impuestos tipo iva
    vat_base_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='VAT Base Amount'
    )
    # base imponible (no se incluyen 0, exento y no gravado)
    vat_taxable_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='VAT Taxable Amount'
    )
    # base iva exento
    vat_exempt_base_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='VAT Exempt Base Amount'
    )
    # base iva no gravado
    vat_untaxed_base_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='VAT Untaxed Base Amount'
    )
    # importe de iva
    vat_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='VAT Amount'
    )
    # importe de otros impuestos
    other_taxes_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='Other Taxes Amount'
    )
    afip_incoterm_id = fields.Many2one(
        'afip.incoterm',
        'Incoterm',
        readonly=True,
        states={'draft': [('readonly', False)]}
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
        compute='_get_concept',
        # store=True,
        selection=[('1', 'Producto / Exportación definitiva de bienes'),
                   ('2', 'Servicios'),
                   ('3', 'Productos y Servicios'),
                   ('4', '4-Otros (exportación)'),
                   ],
        string="AFIP concept",
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

    @api.one
    def _get_argentina_amounts(self):
        """
        """
        vat_taxes = self.tax_line_ids.filtered(
            lambda r: (
                r.tax_id.tax_group_id.type == 'tax' and
                r.tax_id.tax_group_id.tax == 'vat'))
        vat_taxables = vat_taxes.filtered(
            lambda r: (
                r.tax_id.tax_group_id.afip_code not in [0, 1, 2]))

        vat_amount = sum(vat_taxes.mapped('amount'))
        self.vat_tax_ids = vat_taxes
        self.vat_taxable_ids = vat_taxables
        self.vat_amount = vat_amount
        # self.vat_taxable_amount = sum(vat_taxables.mapped('base_amount'))
        self.vat_taxable_amount = sum(vat_taxables.mapped('base'))
        # self.vat_base_amount = sum(vat_taxes.mapped('base_amount'))
        self.vat_base_amount = sum(vat_taxes.mapped('base'))

        # vat exempt values
        # exempt taxes are the ones with code 2
        vat_exempt_taxes = self.tax_line_ids.filtered(
            lambda r: (
                r.tax_id.tax_group_id.type == 'tax' and
                r.tax_id.tax_group_id.tax == 'vat' and
                r.tax_id.tax_group_id.afip_code == 2))
        self.vat_exempt_base_amount = sum(
            vat_exempt_taxes.mapped('base'))
        # self.vat_exempt_base_amount = sum(
        #     vat_exempt_taxes.mapped('base_amount'))

        # vat_untaxed_base_amount values (no gravado)
        # vat exempt taxes are the ones with code 1
        vat_untaxed_taxes = self.tax_line_ids.filtered(
            lambda r: (
                r.tax_id.tax_group_id.type == 'tax' and
                r.tax_id.tax_group_id.tax == 'vat' and
                r.tax_id.tax_group_id.afip_code == 1))
        self.vat_untaxed_base_amount = sum(
            vat_untaxed_taxes.mapped('base'))
        # self.vat_untaxed_base_amount = sum(
        #     vat_untaxed_taxes.mapped('base_amount'))

        # other taxes values
        not_vat_taxes = self.tax_line_ids - vat_taxes
        other_taxes_amount = sum(not_vat_taxes.mapped('amount'))
        self.not_vat_tax_ids = not_vat_taxes
        self.other_taxes_amount = other_taxes_amount

    @api.one
    @api.depends('document_number', 'number')
    def _get_invoice_number(self):
        """ Funcion que calcula numero de punto de venta y numero de factura
        a partir del document number. Es utilizado principalmente por el modulo
        de vat ledger citi
        """
        # TODO mejorar estp y almacenar punto de venta y numero de factura por
        # separado, de hecho con esto hacer mas facil la carga de los
        # comprobantes de compra

        # decidimos obtener esto solamente para comprobantes con doc number
        str_number = self.document_number or False
        if str_number:
            if self.document_type_id.code in ['33', '99', '331', '332']:
                point_of_sale = '0'
                # leave only numbers and convert to integer
                invoice_number = str_number
            # despachos de importacion
            elif self.document_type_id.code == '66':
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
                raise UserError(_(
                    'Could not get invoice number and point of sale for '
                    'invoice id %i') % (self.id))
            self.invoice_number = int(
                re.sub("[^0-9]", "", invoice_number))
            self.point_of_sale_number = int(
                re.sub("[^0-9]", "", point_of_sale))

    @api.one
    @api.depends(
        'invoice_line_ids',
        'invoice_line_ids.product_id',
        'invoice_line_ids.product_id.type',
        'localization',
    )
    def _get_concept(self):
        afip_concept = False
        if self.point_of_sale_type in ['online', 'electronic']:
            # exportaciones
            invoice_lines = self.invoice_line_ids
            product_types = set(
                [x.product_id.type for x in invoice_lines if x.product_id])
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
                # TODO verificar esto, como par expo no existe 3 y existe 4
                # (otros), considermaos que un mixto seria el otros
                if afip_concept == '3':
                    afip_concept = '4'
        self.afip_concept = afip_concept

    @api.multi
    def get_localization_invoice_vals(self):
        self.ensure_one()
        if self.localization == 'argentina':
            commercial_partner = self.partner_id.commercial_partner_id
            currency = self.currency_id.with_context(
                date=self.date_invoice or fields.Date.context_today(self))
            if self.company_id.currency_id == currency:
                currency_rate = 1.0
            else:
                currency_rate = currency.compute(
                    1., self.company_id.currency_id, round=False)
            return {
                'afip_responsability_type_id': (
                    commercial_partner.afip_responsability_type_id.id),
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
                    domain += [
                        ('document_type_id.internal_type',
                            '=', 'credit_note')]
                # else, none credit notes
                else:
                    domain += [
                        ('document_type_id.internal_type',
                            '!=', 'credit_note')]

                # If internal_type in context we try to serch specific document
                # for eg used on debit notes
                internal_type = self._context.get('internal_type', False)
                if internal_type:
                    journal_document_type = journal_document_type.search(
                        domain + [
                            ('document_type_id.internal_type',
                                '=', internal_type)], limit=1)
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

        # check partner has responsability so it will be assigned on invoice
        # validate
        without_responsability = argentinian_invoices.filtered(
            lambda x: not x.commercial_partner_id.afip_responsability_type_id)
        if without_responsability:
            raise UserError(_(
                'The following invoices has a partner without AFIP '
                'responsability: %s' % without_responsability.ids))

        # we check all invoice tax lines has tax_id related
        # we exclude exempt vats and untaxed (no gravados)
        wihtout_tax_id = argentinian_invoices.mapped('tax_line_ids').filtered(
            lambda r: not r.tax_id)
        if wihtout_tax_id:
            raise UserError(_(
                "Some Invoice Tax Lines don't have a tax_id asociated, please "
                "correct them or try to refresh invoice "))

        # check codes has argentinian tax attributes configured
        tax_groups = argentinian_invoices.mapped(
            'tax_line_ids.tax_id.tax_group_id')
        unconfigured_tax_groups = tax_groups.filtered(
            lambda r: not r.type or not r.tax or not r.application)
        if unconfigured_tax_groups:
            raise UserError(_(
                "You are using argentinian localization and there are some tax"
                " groups that are not configured. Tax Groups (id): %s" % (
                    ', '.join(unconfigured_tax_groups.mapped(
                        lambda x: '%s (%s)' % (x.name, x.id))))))

        # self.env['account.invoice.line'].search([
        #     ('invoice_id', 'in', argentinian_invoices.ids),
        #     ('invoice_line_tax_ids.tax_group_id', 'in',
        #         argentinian_invoices.ids),
        #     ])
        # for invoice in argentinian_invoices:
        #     # we check vat base amount is equal to amount untaxed
        #     # usamos una precision de 0.1 porque en algunos casos no pudimos
        #     # arreglar pbñe,as de redondedo
        #     # TODO usar round
        #     if abs(invoice.vat_base_amount - invoice.amount_untaxed) > 0.1:
        #         raise UserError(_(
        #             "Invoice with ID %i has some lines without vat Tax ") % (
        #                 invoice.id))

        # Check except vat invoice
        afip_exempt_codes = ['Z', 'X', 'E', 'N', 'C']
        for invoice in argentinian_invoices:
            special_vat_taxes = invoice.tax_line_ids.filtered(
                lambda r: r.tax_id.tax_group_id.afip_code in [1, 2, 3])
            if (
                    special_vat_taxes and
                    invoice.fiscal_position_id.afip_code
                    not in afip_exempt_codes):
                raise UserError(_(
                    "If you have choose a 0, exempt or untaxed 'tax', "
                    "you must choose a fiscal position with afip code in %s.\n"
                    "* Invoice id %i" % (afip_exempt_codes, invoice.id))
                )

    # TODO check if we can remove this. If we import or get demo data
    # tax_id is not loaded on tax lines, we couldn't find the error
    # so we add this to fix it
    @api.one
    @api.constrains('invoice_line_ids')
    def update_taxes_fix(self):
        context = dict(self._context)
        if context.get('constraint_update_taxes'):
            return True
        self.with_context(constraint_update_taxes=True).compute_taxes()

    # we add fiscal position with fp method instead of directly from partner
    # TODO. this should go in a PR to ODOO
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        fiscal_position = self.env[
            'account.fiscal.position'].get_fiscal_position(self.partner_id.id)
        if fiscal_position:
            self.fiscal_position_id = fiscal_position
        return res

    @api.one
    @api.constrains('date_invoice')
    def set_date_afip(self):
        if self.date_invoice:
            date_invoice = fields.Datetime.from_string(self.date_invoice)
            if not self.afip_service_start:
                self.afip_service_start = date_invoice + relativedelta(day=1)
            if not self.afip_service_end:
                self.afip_service_end = date_invoice + \
                    relativedelta(day=1, days=-1, months=+1)
