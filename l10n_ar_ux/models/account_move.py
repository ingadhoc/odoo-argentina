##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    computed_currency_rate = fields.Float(
        compute='_compute_currency_rate',
        string='Currency Rate (preview)',
        digits=(16, 6),
    )
    l10n_ar_currency_rate = fields.Float(compute='_compute_l10n_ar_currency_rate', store=True)

    @api.depends('reversed_entry_id')
    def _compute_l10n_ar_currency_rate(self):
        """ If it's a credit note on foreign currency and foreing currency is the same as original credit note, then
        we use original invoice rate """
        ar_reversed_other_currency = self.filtered(
            lambda x: x.is_invoice() and x.reversed_entry_id and
            x.company_id.country_id == self.env.ref('base.ar') and
            x.currency_id != x.company_id.currency_id and
            x.reversed_entry_id.currency_id == x.currency_id)
        self.filtered(lambda x: x.move_type == 'entry').l10n_ar_currency_rate = False
        for rec in ar_reversed_other_currency:
            rec.l10n_ar_currency_rate = rec.reversed_entry_id.l10n_ar_currency_rate

    @api.depends('currency_id', 'company_id', 'date', 'invoice_date')
    def _compute_currency_rate(self):
        need_currency_rate = self.filtered(lambda x: x.currency_id and x.company_id and (x.currency_id != x.company_id.currency_id))
        remaining = self - need_currency_rate
        for rec in need_currency_rate:
            if rec.l10n_ar_currency_rate:
                rec.computed_currency_rate = rec.l10n_ar_currency_rate
            else:
                rec.computed_currency_rate = rec.currency_id._convert(
                    1.0, rec.company_id.currency_id, rec.company_id,
                    # para previsualizar lo que sería la tasa usamos la fecha contable, sino usamos la fecha al día de hoy
                    # la fecha contable en facturas de venta realmente está seteada cuando el invoice_date está activo o
                    # posterior a la validación de la factura es por eso que comparamos invoice_date
                    date=rec.date if rec.invoice_date else fields.Date.context_today(rec),
                    round=False)
        remaining.computed_currency_rate = 1.0

    def _get_name_invoice_report(self):
        """Use always argentinian like report (regardless use documents)"""
        self.ensure_one()
        if self.company_id.country_id.code == 'AR':
            return 'l10n_ar.report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        # TODO: add prefix "_l10n_ar" to method use_specific_document_types
        if self.company_id.country_id == self.env.ref('base.ar') and self.journal_id.use_specific_document_types():
            return [
                ('id', 'in', self.journal_id.l10n_ar_document_type_ids.ids),
                '|', ('code', 'in', self._get_l10n_ar_codes_used_for_inv_and_ref()),
                ('internal_type', 'in', ['credit_note'] if self.move_type in ['out_refund', 'in_refund'] else ['invoice', 'debit_note']),
            ]
        return super()._get_l10n_latam_documents_domain()

    def _l10n_ar_include_vat(self):
        self.ensure_one()
        if not self.l10n_latam_use_documents:
            discriminate_taxes = self.journal_id.discriminate_taxes
            if discriminate_taxes == 'yes':
                return False
            elif discriminate_taxes == 'no':
                return True
            else:
                return not (
                    self.company_id.l10n_ar_company_requires_vat and
                    self.partner_id.l10n_ar_afip_responsibility_type_id.code in ['1'] or False)
        return self.l10n_latam_document_type_id.l10n_ar_letter in ['B', 'C', 'X', 'R']

    def _is_manual_document_number(self):
        res = super()._is_manual_document_number()
        # when issuer is supplier de numbering works opposite (supplier numerate invoices, customer encode bill)
        if self.country_code == 'AR' and self.journal_id._l10n_ar_journal_issuer_is_supplier():
            return not res
        return res

    def _post(self, soft=True):
        # estamos haciendo varias cosas acá:
        # 1. para facturas sin documentos guardamos el rate (en l10n_ar solo se hace para las que usan documentos)
        # 2. en vez de que el rate se seete luego de postear (que es lo que l10n_ar) lo hacaemos antes para garantizar que
        # se actualicen los apuntes contables con el rate que efectivamente se va a autilizar
        # hacemos el hack del +1 porque sin eso no termina de actualizar
        # el metodo _set_afip_rate super lo llama pero no va a hacer nada porque ya llega con un de l10n_ar_currency_rate seteado
        not_use_doc_with_currency_ar_invoices = self.filtered(
            lambda x: x.company_id.account_fiscal_country_id.code == "AR" and x.is_invoice(include_receipts=True)
            and x.currency_id != x.company_currency_id and not x.l10n_ar_currency_rate)
        for rec in not_use_doc_with_currency_ar_invoices:
            rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=rec.currency_id,
                        to_currency=rec.company_id.currency_id,
                        company=rec.company_id,
                        date=rec.invoice_date or fields.Date.context_today(rec),
                    )
            rec.write({'l10n_ar_currency_rate': rate + 1, 'tax_totals': rec.tax_totals})
            rec.write({'l10n_ar_currency_rate': rate, 'tax_totals': rec.tax_totals})
        res = super()._post(soft=soft)
        return res

    @api.depends('l10n_latam_available_document_type_ids', 'debit_origin_id')
    def _compute_l10n_latam_document_type(self):
        """ Sobre escribimos este metodo porque es necesario para poder auto calcular el tipo de documento por defecto
        de una nota de debito cuando no hay un debit_origin_id definido, puede ser porque simplemente no haya un
        documento relacionado original o porque hay muchos documentos relacionados pero no puede ser asociados """
        super()._compute_l10n_latam_document_type()
        if self.env.context.get('internal_type') == 'debit_note':
            for rec in self.filtered(lambda x: x.state == 'draft'):
                document_types = rec.l10n_latam_available_document_type_ids._origin
                document_types = document_types.filtered(lambda x: x.internal_type == 'debit_note')
                rec.l10n_latam_document_type_id = document_types and document_types[0].id
