# -*- coding: utf-8 -*-
{
    'author': "Moldeo Interactive,ADHOC SA",
    'category': 'Localization/Argentina',
    'depends': [
        'partner_identification',
    ],
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Títulos de Personería y Tipos de documentos Arentinos',
    'data': [
        # 'data/res_partner_title_data.xml',
        'data/res_partner_id_category_data.xml',
        'data/res_partner_data.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/res_partner_id_category_view.xml',
        'views/res_partner_id_number_view.xml',
    ],
    'demo': [
        'demo/partner_demo.xml',
    ],
    'version': '0.0.1.0.0',
    'post_init_hook': 'post_init_hook',
}
