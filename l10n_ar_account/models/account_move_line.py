##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # useful to group by this field
    afip_responsability_type_id = fields.Many2one(
        related='move_id.afip_responsability_type_id',
        readonly=True,
        auto_join=True,
        # stored required to group by
        store=True,
    )

    @api.model
    def get_tax_move_lines_action(
            self, date_from, date_to, tax_or_base='tax', taxes=None,
            tax_groups=None,
            document_types=None, afip_responsabilities=None,
            f2002_category=None, activity=None, type_tax_use=None,
            company_ids=None, credit_or_debit=None, domain=None):
        domain = self._get_tax_move_lines_domain(
            date_from, date_to, tax_or_base=tax_or_base, taxes=taxes,
            tax_groups=tax_groups,
            document_types=document_types,
            afip_responsabilities=afip_responsabilities,
            f2002_category=f2002_category,
            activity=activity,
            type_tax_use=type_tax_use,
            company_ids=company_ids,
            credit_or_debit=credit_or_debit,
            domain=domain,
        )
        action = self.env.ref('account.action_account_moves_all_tree')
        vals = action.read()[0]
        vals['context'] = {}
        vals['domain'] = domain
        return vals

    @api.model
    def _get_tax_move_lines_balance(
            self, date_from, date_to, tax_or_base='tax', taxes=None,
            tax_groups=None,
            document_types=None, afip_responsabilities=None,
            f2002_category=None, activity=None, type_tax_use=None,
            company_ids=None, credit_or_debit=None, domain=None):
        domain = self._get_tax_move_lines_domain(
            date_from, date_to, tax_or_base=tax_or_base, taxes=taxes,
            tax_groups=tax_groups,
            document_types=document_types,
            afip_responsabilities=afip_responsabilities,
            f2002_category=f2002_category,
            activity=activity,
            type_tax_use=type_tax_use,
            company_ids=company_ids,
            credit_or_debit=credit_or_debit,
            domain=domain,
        )
        balance = self.env['account.move.line'].\
            read_group(domain, ['balance'], [])[0]['balance']
        return balance and -balance or 0.0

    @api.model
    def _get_tax_move_lines_domain(
            self, date_from, date_to, tax_or_base='tax', taxes=None,
            tax_groups=None,
            document_types=None, afip_responsabilities=None,
            f2002_category=None, activity=None, type_tax_use=None,
            company_ids=None, credit_or_debit=None, domain=None):
        """
        Function to be used on reports to get move lines for tax reports
        """
        domain = domain and safe_eval(str(domain)) or []

        if not taxes and not tax_groups or taxes and tax_groups:
            raise UserError(_(
                'You must request tax amounts with tax or tax group'))

        # if tax groups then, no taxes, we get taxes with tax groups
        if tax_groups:
            taxes = self.env['account.tax'].search(
                [('tax_group_id', 'in', tax_groups.ids)])

        if type_tax_use:
            taxes = taxes.filtered(lambda x: x.type_tax_use == type_tax_use)

        domain += [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]

        if tax_or_base == 'tax':
            domain += [('tax_line_id', 'in', taxes.ids)]
        elif tax_or_base == 'base':
            domain += [('tax_ids', 'in', taxes.ids)]
        else:
            raise UserError(_(
                'Type must be "base" or "tax"'))

        if document_types:
            domain += [('move_id.document_type_id', 'in', document_types.ids)]

        if afip_responsabilities:
            domain += [
                ('move_id.afip_responsability_type_id', 'in',
                    afip_responsabilities.ids)]

        # if we send False, we want to search thos products without category
        if f2002_category is not None:
            domain += [
                ('account_id.vat_f2002_category_id', '=', f2002_category.id)]

        # if we send False, we want to search thos products without category
        if activity is not None:
            domain += [
                ('account_id.afip_activity_id', '=', activity.id)]

        # usado para discriminar credito/debito fiscal de restitucion (usar
        # junto con tipo de impuesto)
        if credit_or_debit:
            if credit_or_debit == 'credit':
                domain += [('debit', '=', 0.0)]
            else:
                domain += [('credit', '=', 0.0)]

        if company_ids:
            domain += [('company_id', 'in', company_ids)]

        _logger.debug('Tax domain getted: %s' % domain)
        return domain
