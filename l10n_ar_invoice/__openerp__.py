# -*- coding: utf-8 -*-
{'active': False,
 'author': 'OpenERP - Team de Localizaci\xc3\xb3n Argentina',
 'category': 'Localization/Argentina',
 'depends': [
     'account',
     'l10n_ar_base',
     'l10n_ar_base_vat',
 ],
 'description': """
Facturación y Documentos AFIP - Argentina
=========================================
Para actualizar el plan de cuentas de datos demo:
-------------------------------------------------
* borrar la parte de account.chart
* reemplazar ".template" por nada
* reemplazar <!-- <field name="company_id" ref=""/> --> por <field name="company_id" ref="company_ri"/>
* reemplazar <field name="chart_template_id" ref="ri_l10nAR_chart_template"/> por <field name="company_id" ref="company_ri"/>


""",
 'init_xml': [],
 'installable': True,
 'license': 'AGPL-3',
 'name': 'Facturación y Documentos AFIP - Argentina',
 'demo': [
     'demo/res_country_state_demo.xml',
     'demo/partner_demo.xml',
     'demo/company_demo.xml',
     # TODO tal vez sea mejor estos dos ejecutarlos con una accion ya que al hacer un init dan error porque ya existen movimientos
     'demo/fiscal_year_mono_demo.xml',
     'demo/fiscal_year_ri_demo.xml',
     'demo/account_chart_respinsc.xml',
     'demo/account_demo.xml',
     'demo/ri_purchase_invoice_demo.xml',
     'demo/ri_sale_invoice_demo.xml',
    ],
 'test': [
          # test cases should be re-writed
          # 'test/products.yml',
          # 'test/partners.yml',
          # 'test/com_ri1.yml',
          # 'test/com_ri2.yml',
          # 'test/com_rm1.yml',
          # 'test/inv_ri2ri.yml',
          # 'test/inv_rm2ri.yml',
          # 'test/inv_ri2rm.yml',
          # 'test/bug_1042944.yml'
          ],
 'data': [
     'security/l10n_ar_invoice_security.xml',
     'data/responsability.xml',
     'data/afip.incoterm.csv',
     'data/afip.document_letter.csv',
     'data/afip.document_class.csv',
     'data/document_type.xml',
     'data/partner.xml',
     'data/country.xml',
     'data/res.currency.csv',
     'data/fiscal_position.xml',
     'data/res.country.csv',
     'data/product.uom.csv',
     'data/res_partner.xml',
     # 'data/decimal_precision_data.xml', probando si no es necesario
     'view/partner_view.xml',
     'view/company_view.xml',
     'view/country_view.xml',
     'view/afip_menuitem.xml',
     'view/product_uom_view.xml',
     'view/fiscal_position_view.xml',
     'view/afip_document_letter_view.xml',
     'view/afip_document_type_view.xml',
     'view/afip_responsability_view.xml',
     'view/afip_document_class_view.xml',
     'view/afip_point_of_sale_view.xml',
     'view/account_journal_afip_document_class_view.xml',
     'view/account_tax_code_view.xml',
     'view/tax_code_template_view.xml',
     'view/journal_view.xml',
     'view/invoice_view.xml',
     'view/account_move_view.xml',
     'view/account_move_line_view.xml',
     'view/currency_view.xml',
     'view/afip_incoterm_view.xml',
     'invoice_template.xml',
     'security/ir.model.access.csv',
     'security/l10n_ar_invoice_security.xml',
 ],
 'version': '2.7.243',
 }
