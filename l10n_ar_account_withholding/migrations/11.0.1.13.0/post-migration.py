from openupgradelib import openupgrade
import logging

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    """ same fix as on account_multic_fix but also here because if this module
    is installed the it may raise errors on account_multic_fix upgrade due
    to inherited tax compute method not loaded yet
    """
    for company in env['res.company'].search([]):
        for rec in env['account.invoice'].search([
                ('company_id', '!=', company.id),
                ('date_invoice', '>=', '2018-01-01')]):
            try:
                compute_price(rec)
            except Exception:
                _logger.warning(
                    'Could not fix invoice %s. The databases may have custom '
                    'taxes. You can run the script manually.')


def compute_price(invoice):
    currency = invoice.currency_id or None
    partner = invoice.partner_id
    if invoice.currency_id == invoice.company_id.currency_id:
        return True
    sign = invoice.type in ['in_refund', 'out_refund'] and -1 or 1
    for line in invoice.invoice_line_ids:
        self = line
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(
                price, currency, self.quantity,
                product=self.product_id, partner=partner)
        price_subtotal_signed = \
            taxes['total_excluded'] if taxes else self.quantity * price
        if invoice.currency_rate:
            price_subtotal_signed = currency.round(
                invoice.currency_rate * self.price_subtotal)
        else:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(
                company_id=self.company_id.id,
                date=self.invoice_id._get_currency_rate_date()).compute(
                    price_subtotal_signed,
                    self.invoice_id.company_id.currency_id)
        self.price_subtotal_signed = price_subtotal_signed * sign
