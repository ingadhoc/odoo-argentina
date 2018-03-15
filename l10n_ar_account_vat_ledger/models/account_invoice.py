##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # TODO podriamos mejorar y no requerir todos estos y usar alguno de los
    # nativos company signed
    # no gravado en iva
    # cc_vat_untaxed = fields.Monetary(
    cc_vat_untaxed_base_amount = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. VAT Untaxed',
    )
    # company currency default odoo fields
    cc_amount_total = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. Total',
    )
    cc_amount_untaxed = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. Untaxed',
    )
    cc_amount_tax = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. Tax',
    )
    # von iva
    cc_vat_amount = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. VAT Amount',
    )
    cc_other_taxes_amount = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. Other Taxes Amount'
    )
    cc_vat_exempt_base_amount = fields.Monetary(
        compute="_get_currency_values",
        string='Company Cur. VAT Exempt Base Amount'
    )

    @api.multi
    @api.depends('currency_id')
    def _get_currency_values(self):
        # TODO si traer el rate de esta manera no resulta (por ej. porque
        # borran una linea de rate), entonces podemos hacerlo desde el move
        # mas o menos como hace account_invoice_currency o viendo el total de
        # debito o credito de ese mismo
        for rec in self:
            currency = rec.currency_id.with_context(
                date=rec.date_invoice or fields.Date.context_today(rec))
            if not currency:
                return False
            if rec.company_id.currency_id == currency:
                rec.cc_amount_untaxed = rec.amount_untaxed
                rec.cc_amount_tax = rec.amount_tax
                rec.cc_amount_total = rec.amount_total
                rec.cc_vat_untaxed_base_amount = rec.vat_untaxed_base_amount
                rec.cc_vat_amount = rec.vat_amount
                rec.cc_other_taxes_amount = rec.other_taxes_amount
                rec.cc_vat_exempt_base_amount = rec.vat_exempt_base_amount
                # rec.currency_rate = 1.0
            else:
                # nueva modalidad de currency_rate
                currency_rate = rec.currency_rate
                # TODO borrar
                # currency_rate = currency.compute(
                #     1.0, rec.company_id.currency_id, round=False)
                # otra alternativa serua usar currency.compute con round true
                # para cada uno de estos valores
                # rec.currency_rate = currency_rate
                rec.cc_amount_untaxed = currency.round(
                    rec.amount_untaxed * currency_rate)
                rec.cc_amount_tax = currency.round(
                    rec.amount_tax * currency_rate)
                rec.cc_amount_total = currency.round(
                    rec.amount_total * currency_rate)
                rec.cc_vat_untaxed_base_amount = currency.round(
                    rec.vat_untaxed_base_amount * currency_rate)
                rec.cc_vat_amount = currency.round(
                    rec.vat_amount * currency_rate)
                rec.cc_other_taxes_amount = currency.round(
                    rec.other_taxes_amount * currency_rate)
                rec.cc_vat_exempt_base_amount = currency.round(
                    rec.vat_exempt_base_amount * currency_rate)

    @api.multi
    def invoice_validate(self):
        AccountVatLedger = self.env['account.vat.ledger']
        for invoice in self:
            ledger_ids = AccountVatLedger.sudo().search([
                ('state', '=', 'presented'),
                ('company_id', '=', invoice.company_id.id),
                ('journal_ids.id', '=', invoice.journal_id.id),
                ('date_from', '<=', invoice.date),
                ('date_to', '>=', invoice.date)])
            if ledger_ids:
                raise UserError(_(
                    "You can't validate an invoice of this date if the "
                    "VAT Ledger Report has already been presented.\r\n"
                    "You need to manually set the Accounting Date."))
        return super(AccountInvoice, self).invoice_validate()
