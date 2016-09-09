# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import UserError
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
    vat_base_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='VAT Base Amount'
    )
    vat_exempt_base_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='VAT Exempt Base Amount'
    )
    # TODO borrar, no los necesitariamos mas porque modificamos compute all
    # para que cree estos impuestos
    # base iva cero (tenemos que agregarlo porque odoo no crea las lineas para
    # impuestos con valor cero)
    # vat_zero_base_amount = fields.Monetary(
    #     compute="_get_argentina_amounts",
    #     string='VAT Zero Base Amount'
    #     )
    # no gravado en iva (tenemos que agregarlo porque odoo no crea las lineas
    # para impuestos con valor cero)
    vat_untaxed_base_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='VAT Untaxed Base Amount'
    )
    vat_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='VAT Amount'
    )
    other_taxes_amount = fields.Monetary(
        compute="_get_argentina_amounts",
        string='Other Taxes Amount'
    )
    vat_tax_ids = fields.One2many(
        compute="_get_argentina_amounts",
        comodel_name='account.invoice.tax',
        string='VAT Taxes'
    )
    not_vat_tax_ids = fields.One2many(
        compute="_get_argentina_amounts",
        comodel_name='account.invoice.tax',
        string='Not VAT Taxes'
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
        string='Service Start Date'
    )
    afip_service_end = fields.Date(
        string='Service End Date'
    )

    @api.one
    def _get_argentina_amounts(self):
        """
        """
        vat_taxes = self.tax_line_ids.filtered(
            lambda r: (
                r.tax_id.tax_group_id.type == 'tax' and
                r.tax_id.tax_group_id.tax == 'vat' and
                r.tax_id.tax_group_id.afip_code not in [1, 2]))

        vat_amount = sum(vat_taxes.mapped('amount'))
        self.vat_tax_ids = vat_taxes
        self.vat_amount = vat_amount
        self.vat_base_amount = sum(vat_taxes.mapped('base_amount'))

        # vat exempt values
        # exempt taxes are the ones with code 2
        vat_exempt_taxes = self.tax_line_ids.filtered(
            lambda r: (
                r.tax_id.tax_group_id.type == 'tax' and
                r.tax_id.tax_group_id.tax == 'vat' and
                r.tax_id.tax_group_id.afip_code == 2))
        self.vat_exempt_base_amount = sum(
            vat_exempt_taxes.mapped('base_amount'))

        # vat_untaxed_base_amount values (no gravado)
        # vat exempt taxes are the ones with code 1
        vat_untaxed_taxes = self.tax_line_ids.filtered(
            lambda r: (
                r.tax_id.tax_group_id.type == 'tax' and
                r.tax_id.tax_group_id.tax == 'vat' and
                r.tax_id.tax_group_id.afip_code == 1))
        self.vat_untaxed_base_amount = sum(
            vat_untaxed_taxes.mapped('base_amount'))

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
            if self.document_type_id.code in [33, 99, 331, 332]:
                point_of_sale = '0'
                # leave only numbers and convert to integer
                invoice_number = str_number
            # despachos de importacion
            elif self.document_type_id.code == 66:
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
            if self.document_type_id.code in [19, 20, 21]:
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
            currency_rate = self.currency_id.compute(
                1., self.company_id.currency_id)
            return {
                'afip_responsability_type_id': (
                    commercial_partner.afip_responsability_type_id.id),
                'currency_rate': currency_rate,
            }
        else:
            return super(
                AccountInvoice, self).get_localization_invoice_vals()

    @api.multi
    def _get_available_journal_document_types(self):
        """
        This function search for available document types regarding:
        * Journal
        * Partner
        * Company
        * Documents configuration
        If needed, we can make this funcion inheritable and customizable per
        localization
        """
        self.ensure_one()
        if self.localization != 'argentina':
            return super(
                AccountInvoice, self)._get_available_journal_document_types()
        invoice_type = self.type

        journal_document_types = journal_document_type = self.env[
            'account.journal.document.type']

        if invoice_type in [
                'out_invoice', 'in_invoice', 'out_refund', 'in_refund']:

            if self.use_documents:

                letters = self.journal_id.get_journal_letter(
                    counterpart_partner=self.commercial_partner_id)

                domain = [
                    ('journal_id', '=', self.journal_id.id),
                    '|',
                    ('document_type_id.document_letter_id', 'in', letters.ids),
                    ('document_type_id.document_letter_id', '=', False),
                ]

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
            other_document_types = (
                self.commercial_partner_id.other_document_type_ids)

            domain = [
                ('journal_id', '=', self.journal_id.id),
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
                " tax group that are not configured. Tax Groups ids: %s" % (
                    unconfigured_tax_groups.ids)))

        for invoice in argentinian_invoices:
            # we check vat base amount is equal to amount untaxed
            # usamos una precision de 0.1 porque en algunos casos no pudimos
            # arreglar pbñe,as de redondedo
            if abs(invoice.vat_base_amount - invoice.amount_untaxed) > 0.1:
                raise UserError(_(
                    "Invoice with ID %i has some lines without vat Tax ") % (
                        invoice.id))

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
    @api.constrains('invoice_line_ids')
    def update_taxes_fix(self):
        context = dict(self._context)
        if context.get('constraint_update_taxes'):
            return True
        self.with_context(constraint_update_taxes=True).compute_taxes()
