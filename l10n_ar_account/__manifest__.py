{
    "name": "Módulo base de Contabilidad Argentina",
    'version': '11.0.1.23.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA,Moldeo Interactive,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'account_document',
        'l10n_ar_partner',
        'l10n_ar_bank',
        # agregamos esta dependencia ya que el fix que hace ese modulo
        # es fundamental para que el importa base de los impuestos se calcule
        # bien en los reembolsos.
        'account_fix',
        # para padron de afip
        'l10n_ar_afipws',
        # para guardar el link entre facturas y NC
        # el modulo tiene errores en los test (probado solo con odoo y tmb)
        # 'account_invoice_refund_link',
        # no es una dependencia en si (salvo para datos demo) pero si es
        # necesario por como implemenamos la localizacion
        # 'account_invoice_tax_wizard',
    ],
    'external_dependencies': {
        'python': ['pyafipws', 'pysimplesoap.client'],
    },
    'data': [
        'wizard/res_partner_update_from_padron_wizard_view.xml',
        'wizard/res_config_settings_view.xml',
        'data/menuitem.xml',
        'data/product_data.xml',
        'data/base_validator_data.xml',
        'data/afip_responsability_type.xml',
        'data/account_document_letter.xml',
        # los cargamos con csv pero los hacemos no actualizables con un hook
        'data/account.document.type.csv',
        'data/afip_incoterm.xml',
        'data/res_country_afip_code.xml',
        'data/res_country_cuit.xml',
        'data/product_uom.xml',
        'data/res_currency.xml',
        'data/res_partner.xml',
        'data/account_tax_group.xml',
        'data/res_country_group_data.xml',
        'data/afip_vat_f2002_category_data.xml',
        'data/account_account_tag.xml',
        # TODO analizar y migrar
        # 'data/account_financial_report_data.xml',
        # 'data/account_payment_term.xml',
        'report/account_ar_vat_line_view.xml',
        'view/account_move_line_view.xml',
        'view/account_move_view.xml',
        'view/res_partner_view.xml',
        'view/res_company_view.xml',
        'view/afip_menuitem.xml',
        'view/afip_incoterm_view.xml',
        'view/account_account_view.xml',
        'view/res_country_view.xml',
        'view/res_currency_view.xml',
        'view/account_fiscal_position_view.xml',
        'view/product_uom_view.xml',
        'view/account_journal_view.xml',
        'view/account_invoice_view.xml',
        'view/afip_responsability_type_view.xml',
        'view/account_document_letter_view.xml',
        'view/account_document_type_view.xml',
        'view/product_template_view.xml',
        'view/afip_activity_view.xml',
        'view/afip_concept_view.xml',
        'view/afip_tax_view.xml',
        'report/invoice_analysis.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'demo': [
        'demo/partner_demo.xml',
        'demo/company_demo.xml',
    ],
    'images': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': 'post_init_hook',
}
