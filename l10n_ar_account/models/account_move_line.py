# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _
from openerp.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def get_tax_move_lines_action(
            self, date_from, date_to, tax_or_base='tax', taxes=None,
            tax_groups=None,
            document_types=None, afip_responsability=None,
            f2002_category=None):
        domain = self._get_tax_move_lines_domain(
            date_from, date_to, tax_or_base=tax_or_base, taxes=taxes,
            tax_groups=tax_groups,
            document_types=document_types,
            afip_responsability=afip_responsability,
            f2002_category=f2002_category)
        action = self.env.ref('account.action_account_moves_all_tree')
        vals = action.read()[0]
        vals['context'] = {}
        vals['domain'] = domain
        return vals

    @api.multi
    def _get_tax_move_lines_balance(
            self, date_from, date_to, tax_or_base='tax', taxes=None,
            tax_groups=None,
            document_types=None, afip_responsability=None,
            f2002_category=None):
        domain = self._get_tax_move_lines_domain(
            date_from, date_to, tax_or_base=tax_or_base, taxes=taxes,
            tax_groups=tax_groups,
            document_types=document_types,
            afip_responsability=afip_responsability,
            f2002_category=f2002_category)
        _logger.info('Getting tax balance for domain %s' % domain)
        balance = self.env['account.move.line'].\
            read_group(domain, ['balance'], [])[0]['balance']
        print 'balance', balance
        return balance and -balance or 0.0

    @api.model
    def _get_tax_move_lines_domain(
            self, date_from, date_to, tax_or_base='tax', taxes=None,
            tax_groups=None,
            document_types=None, afip_responsability=None,
            f2002_category=None):
        """
        Function to be used on reports to get move lines for tax reports
        """
        if not taxes and not tax_groups or taxes and tax_groups:
            raise UserError(_(
                'You must request tax amounts with tax or tax group'))

        # if tax groups then, no taxes, we get taxes with tax groups
        if tax_groups:
            taxes = self.env['account.tax'].search(
                [('tax_group_id', 'in', tax_groups.ids)])

        domain = [
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

        if afip_responsability:
            domain += [
                ('move_id.partner_id.afip_responsability_type_id', '=',
                    afip_responsability.id)]

        # if we send False, we want to search thos products without category
        if f2002_category:
            domain += [
                ('product_id.vat_f2002_category_id', '=',
                    f2002_category.id)]
        if f2002_category is False:
            domain += [
                '|', ('product_id', '=', False),
                ('product_id.vat_f2002_category_id', '=', False)]
        return domain
        # return self.env['account.move.line'].search(domain)
