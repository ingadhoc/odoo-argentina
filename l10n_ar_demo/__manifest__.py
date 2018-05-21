##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'More demo data for Argentina Localization',
    'version': '11.0.1.0.0',
    'category': 'Accounting',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA,Odoo Community Association (OCA)',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'account_invoicing',
        'l10n_ar_afipws_fe',
        'l10n_ar_chart',
        'l10n_ar_account_withholding',
    ],
    'data': [
    ],
    'demo': [
        # De l10n_ar_chart
        # para datos demo agregamos alicuotas a las percepciones aplicadas y
        # sufridas
        '../l10n_ar_account/demo/account_tax_template_demo.xml',
        '../l10n_ar_chart/data/account_chart_template.yml',
        # TODO los productos se podrian cargar directamente en l10n_ar_account
        '../l10n_ar_account/demo/product_product_demo.xml',
        '../l10n_ar_account/demo/account_customer_invoice_demo.yml',
        '../l10n_ar_account/demo/account_customer_expo_invoice_demo.yml',
        '../l10n_ar_account/demo/account_customer_invoice_validate_demo.yml',
        '../l10n_ar_account/demo/account_customer_refund_demo.yml',
        '../l10n_ar_account/demo/account_supplier_invoice_demo.yml',
        '../l10n_ar_account/demo/account_supplier_refund_demo.yml',
        # todo ver si usamos esto o un demo con el de groups
        # '../l10n_ar_account/demo/account_payment_demo.yml',
        '../l10n_ar_account/demo/account_other_docs_demo.yml',
        # we add this file only fot tests run by odoo, we could use
        # an yml testing if config.options['test_enable'] and only load it
        # in that case
        '../l10n_ar_account/demo/account_journal_demo.xml',
        # '../account/demo/account_bank_statement.yml',
        # '../account/demo/account_invoice_demo.yml',

        # de l10n_ar_account_withholding (no estarian los diarios creados acá)
        # '../l10n_ar_account_withholding/demo/customer_payment_demo.xml',
        # '../l10n_ar_account_withholding/demo/supplier_payment_demo.xml',

        # de l10n_ar_afipws_fe
        '../l10n_ar_afipws_fe/demo/account_journal_expo_demo.yml',
        # no podemos cargar este archivo porque usa el mismo prefijo de modulo
        # y entonces sobree escribe las facturas de arriba, habria que
        # duplicarlo
        # '../l10n_ar_account/demo/account_customer_expo_invoice_demo.yml',
        '../l10n_ar_afipws_fe/demo/account_journal_demo.yml',
        # idem para las de expo
        # '../l10n_ar_account/demo/account_customer_invoice_demo.yml',
        '../l10n_ar_afipws_fe/demo/account_journal_demo_without_doc.yml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
