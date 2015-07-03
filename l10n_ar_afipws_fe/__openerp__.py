# -*- coding: utf-8 -*-
{'active': False,
    'author': 'odoo - Team de Localización Argentina',
    'category': 'Localization/Argentina',
    'demo': [],
    'depends': [
        'l10n_ar_afipws',
        ],
    'description': """
API y GUI para acceder a las Web Services de Factura Electrónica de la AFIP
===========================================================================
TODO analizar que hacemos con la clase afip error, a ver si la aprovechamos en algun lugar
""",
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Argentina - Web Services de Factura Electrónica del AFIP',
    'demo': [
     # 'demo/afip.point_of_sale.csv',
     # 'demo/account.journal.csv',
     # 'demo/account.invoice.csv',
    ],
    'data': [
        'wizard/afip_ws_consult_wizard_view.xml',
        'views/invoice_view.xml',
        'views/journal_afip_document_class_view.xml',
        'views/wsfe_error_view.xml',
        'views/afip_point_of_sale_view.xml',
        'data/afip.wsfe_error.csv',
        'security/ir.model.access.csv',
        # 'views/afipws_fe_config_view.xml',
        # 'wizard/query_invoices_view.xml',
        # 'wizard/validate_invoices_view.xml',
        # 'wizard/res_config_view.xml',
    ],
    'version': '2.7.244',
 }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
