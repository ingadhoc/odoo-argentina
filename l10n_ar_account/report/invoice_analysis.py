##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api
from odoo import tools


class AccountInvoiceLineReport(models.Model):

    _name = "account.invoice.line.report"
    _description = "Invoices Statistics"
    _auto = False

    price_unit = fields.Float('Unit Price', readonly=True)
    price_subtotal = fields.Float(
        'Subtotal', readonly=True, group_operator="sum")
    quantity = fields.Float('Quantity', readonly=True, group_operator="sum")
    discount = fields.Float('Discount (%)', readonly=True)
    price_gross_subtotal = fields.Float(
        'Gross Subtotal', readonly=True, group_operator="sum")
    discount_amount = fields.Float(
        'Discount Amount', readonly=True, group_operator="sum")
    # period_id = fields.Many2one('account.period', 'Period', readonly=True)
    # fiscalyear_id = fields.Many2one(
    #     'account.fiscalyear', 'Fiscal Year', readonly=True)
    date_due = fields.Date('Due Date', readonly=True)
    number = fields.Char(string='Number', size=128, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('open', 'Open'),
        ('paid', 'Done'),
        ('cancel', 'Cancelled')
    ], 'Invoice State', readonly=True)
    account_id = fields.Many2one('account.account', readonly=True)
    document_type_id = fields.Many2one('account.document.type', readonly=True)
    date = fields.Date('Accounting Date', readonly=True)
    date_invoice = fields.Date('Date Invoice', readonly=True)
    date_invoice_from = fields.Date(
        compute=lambda *a, **k: {}, method=True, string="Date Invoice from")
    date_invoice_to = fields.Date(
        compute=lambda *a, **k: {}, method=True, string="Date Invoice to")
    amount_total = fields.Float(
        'Invoice Total', readonly=True, group_operator="sum")
    barcode = fields.Char('Barcode', size=13, readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    name_template = fields.Char(
        string="Product by text", size=128, readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    customer = fields.Boolean(
        'Is a Customer',
        help="Check this box if this contact is a customer.", readonly=True)
    supplier = fields.Boolean(
        'Vendor',
        help="Check this box if this contact is a vendor."
        " If it's not checked,"
        "purchase people will not see it when encoding a purchase order.",
        readonly=True)
    journal_id = fields.Many2one('account.journal', 'Journal', readonly=True)
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Supplier Invoice'),
        ('out_refund', 'Customer Refund'),
        ('in_refund', 'Supplier Refund'),
    ], 'Type', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesman', readonly=True)
    state_id = fields.Many2one('res.country.state', 'State', readonly=True)
    afip_activity_id = fields.Many2one(
        'afip.activity',
        'AFIP Activity',
        help='AFIP activity, used for IVA f2002 report',
        readonly=True,
    )
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    product_category_id = fields.Many2one(
        'product.category', 'Category', readonly=True)
    account_analytic_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account',
        readonly=True)
    price_subtotal_signed = fields.Float(
        'Amount Signed',
        readonly=True,
        group_operator="sum"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        readonly=True
    )

    _order = 'id'

    @api.model_cr
    def init(self):
        cr = self.env.cr

        tools.drop_view_if_exists(cr, 'account_invoice_line_report')
        cr.execute("""
        CREATE OR REPLACE VIEW account_invoice_line_report AS (
        SELECT
        "account_invoice_line"."id" AS "id",
        "account_invoice_line"."price_unit" AS "price_unit",
        "account_invoice_line"."discount" AS "discount",
        "account_invoice_line"."account_id" AS "account_id",
        "account_invoice_line"."account_analytic_id" AS "account_analytic_id",
        "account_invoice_line"."price_subtotal_signed" AS
         "price_subtotal_signed",
        case when "account_invoice"."type" in ('in_refund','out_refund') then
                               -("account_invoice_line"."quantity")
                              else
                               "account_invoice_line"."quantity"
                              end as "quantity",
        case when "account_invoice"."type" in ('in_refund','out_refund') then
                               -("account_invoice_line"."price_subtotal")
                              else
                               "account_invoice_line"."price_subtotal"
                              end as "price_subtotal",

      -- Campos Calculados
        case when "account_invoice"."type" in ('in_refund','out_refund') then
                               -("price_unit" * "quantity")
                              else
                               ("price_unit" * "quantity")
                              end as "price_gross_subtotal",

        case when "account_invoice"."type" in ('in_refund','out_refund') then
                               -("price_unit" * "quantity" * ("discount"/100))
                              else
                               ("price_unit" * "quantity" * ("discount"/100))
                              end as "discount_amount",

        "account_invoice_line"."partner_id" AS "partner_id",--n
        "account_invoice_line"."product_id" AS  "product_id", --n
        "account_invoice"."date_due" AS "date_due",
        COALESCE("account_invoice"."document_number",
        "account_invoice"."number") AS "number",
        "account_invoice"."currency_id" AS "currency_id",
        "account_invoice"."journal_id" AS "journal_id",--n
        "account_invoice"."user_id" AS "user_id",--n
        "account_invoice"."company_id" AS "company_id",--n
        "account_invoice"."type" AS "type",
        "account_invoice"."state_id" AS "state_id",--n

        "account_invoice"."document_type_id" AS "document_type_id",
        "account_invoice"."state" AS "state",
        "account_invoice"."date" AS "date",
        "account_invoice"."date_invoice" AS "date_invoice",

        "account_invoice"."amount_total" AS "amount_total",
        "product_product"."barcode" AS "barcode",
        "product_template"."name" AS "name_template",

        "account_account"."afip_activity_id" AS "afip_activity_id",

        "product_template"."categ_id" as "product_category_id", --n
        "res_partner"."customer" AS "customer",
        "res_partner"."supplier" AS "supplier"
        -- "account_invoice"."period_id" AS "period_id",
        -- "account_period"."fiscalyear_id" AS "fiscalyear_id"

        FROM "account_invoice_line" "account_invoice_line"
        INNER JOIN "account_invoice" "account_invoice"
        ON ("account_invoice_line"."invoice_id" = "account_invoice"."id")
        LEFT JOIN "product_product" "product_product"
        ON ("account_invoice_line"."product_id" = "product_product"."id")
        INNER JOIN "res_partner" "res_partner"
        ON ("account_invoice"."partner_id" = "res_partner"."id")
        INNER JOIN "account_account" "account_account"
        ON ("account_invoice_line"."account_id" = "account_account"."id")
        LEFT JOIN "product_template" "product_template"
        ON ("product_product"."product_tmpl_id" = "product_template"."id")
        -- INNER JOIN "public"."account_period" "account_period"
        -- ON ("account_invoice"."period_id" = "account_period"."id")
        ORDER BY number ASC
              )""")
