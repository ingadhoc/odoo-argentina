# -*- coding: utf-8 -*-
{'active': False,
    'author': 'odoo - Team de Localización Argentina',
    'category': 'Localization/Argentina',
    'demo': [],
    'depends': ['l10n_ar_wsafip', 'l10n_ar_invoice'],
    'description': """
API y GUI para acceder a las Web Services de Factura Electrónica de la AFIP
""",
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Argentina - Web Services de Factura Electrónica del AFIP',
    'test': ['test/test_key.yml',
             'test/partners.yml',
             'test/products.yml',
             'test/com_ri1.yml',
             'test/com_ri2.yml',
             'test/com_rm1.yml',
             'test/journal.yml'],
    'demo': [
     # 'demo/afip.point_of_sale.csv',
     # 'demo/account.journal.csv',
     # 'demo/account.invoice.csv',
    ],
    'data': [
        'views/invoice_view.xml',
        'views/journal_afip_document_class_view.xml',
        'views/wsfe_error_view.xml',
        'views/wsafip_fe_config_view.xml',
        'data/afip.wsfe_error.csv',
        'data/wsafip_server.xml',
        'security/ir.model.access.csv',
        'wizard/query_invoices_view.xml',
        'wizard/validate_invoices_view.xml',
        'views/res_config_view.xml',
    ],
    'version': '2.7.244',
 }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
