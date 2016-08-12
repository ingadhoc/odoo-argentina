# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """ We change this module search because odoo in module account
        loads l10n_ar chart on post_install "_auto_install_l10n"
        """
        new_args = []
        for arg in args:
            if arg[0] == 'name' and arg[1] == '=' and arg[2] == 'l10n_ar':
                # we overrwite because arg can be a tuple or a list
                # tuple does not support item assignment
                # arg = (arg[0], arg[1], 'l10n_ar_chart')
                arg = list(arg)
                arg[2] = 'l10n_ar_chart'
            elif arg[0] == 'name' and arg[1] == 'in' and 'l10n_ar' in arg[2]:
                arg = list(arg)
                arg[2] = [
                    'l10n_ar_chart' if x == 'l10n_ar' else x for x in arg[2]]
            new_args.append(arg)
        return super(IrModuleModule, self).search(
            new_args, offset, limit, order, count=count)


class argentinian_base_configuration(models.TransientModel):
    _name = 'argentinian.base.config.settings'
    _inherit = 'res.config.settings'

    module_l10n_ar_bank_cbu = fields.Boolean(
        'Add CBU on bank account information',
        help="""Installs the l10n_ar_bank_cbu module.""")
    module_l10n_ar_chart_generic = fields.Boolean(
        'Generic Argentinian Chart of Account',
        help="""Installs the l10n_ar_chart_generic module.""")
    module_l10n_ar_bank = fields.Boolean(
        'Banks of Argentina',
        help="Installs the l10n_ar_bank module that create banks of Argetina "
        " based on a webservice")
    module_l10n_ar_base_vat = fields.Boolean(
        'Argentinian VAT validation',
        help="Installs the l10n_ar_base_vat module that extends base_vat"
        " modules so that you can add argentinian VATs (usually called"
        "cuit/cuil)")
    module_l10n_ar_invoice = fields.Boolean(
        'Argentinian invoicing and other documents Management',
        help="Installs the l10n_ar_invoice module. It creates some clases"
        " to manage afip functionality, for example document class, journal"
        " class, document letters, vat categories, etc.")
    module_l10n_ar_partner_title = fields.Boolean(
        'Partner reference and titles usually used in Argentina',
        help="""Installs the l10n_ar_partner_title module. """)
    module_l10n_ar_states = fields.Boolean(
        'Argentinian States',
        help="""Installs the l10n_ar_states module. """)
    module_l10n_ar_vat_reports = fields.Boolean(
        'Argentinian Sale/Purchase Vat Reports',
        help="""Installs the l10n_ar_vat_reports module. """)
    module_l10n_ar_hide_receipts = fields.Boolean(
        'Hide sale/purchase receipts menus.',
        help="""Installs the l10n_ar_hide_receipts module. """)
    module_account_accountant = fields.Boolean(
        'Manage Financial and Analytic Accounting.',
        help="""Installs the account_accountant module. """)
    module_l10n_ar_afipws_fe = fields.Boolean(
        'Use Electronic Invoicing.',
        help="""Installs the l10n_ar_afipws_fe module. """)
    module_l10n_ar_account_vat_ledger = fields.Boolean(
        'Add Account VAT Ledger models and report.',
        help="""Installs the l10n_ar_account_vat_ledger module. """)
    module_l10n_ar_account_vat_ledger_city = fields.Boolean(
        'Add Account VAT Ledger TAX entity information requirements by file.',
        help="""Installs the l10n_ar_account_vat_ledger_city module. """)
    module_l10n_ar_chart_generic_withholding = fields.Boolean(
        'Add generic withholding management.',
        help="""Installs the l10n_ar_chart_generic_withholding module. """)

    # Sales
    module_l10n_ar_invoice_sale = fields.Boolean(
        'Add availabilty to use VAT included or not on sales',
        help="""Installs the l10n_ar_invoice_sale module.""")

    # Aeroo reports
    module_l10n_ar_aeroo_voucher = fields.Boolean(
        'Argentinian Like Voucher Aeroo Report',
        help="""Installs the module_l10n_ar_aeroo_voucher module.""")
    module_l10n_ar_aeroo_invoice = fields.Boolean(
        'Argentinian Aeroo Like Invoice Report',
        help="""Installs the module_l10n_ar_aeroo_invoice module.""")
    module_l10n_ar_aeroo_einvoice = fields.Boolean(
        'Argentinian Aeroo Like Electronic Invoice Report',
        help="""Installs the module_l10n_ar_aeroo_einvoice module.""")
    module_l10n_ar_aeroo_stock = fields.Boolean(
        'Argentinian Aeroo Like Remit Report',
        help="""Installs the l10n_ar_aeroo_stock module.""")
    module_l10n_ar_aeroo_purchase = fields.Boolean(
        'Argentinian Aeroo Like Purchase Reports',
        help="""Installs the l10n_ar_aeroo_purchase module.""")
    module_l10n_ar_aeroo_sale = fields.Boolean(
        'Argentinian Aeroo Like Sale Reports',
        help="""Installs the l10n_ar_aeroo_sale module.""")
    # module_l10n_ar_aeroo_receipt = fields.Boolean(
    #     'Argentinian Aeroo Like Receipt Report',
    #     help="""Installs the l10n_ar_aeroo_receipt module.""")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
