# -*- coding: utf-8 -*-
{
    'author': "Moldeo Interactive,ADHOC SA",
    'category': 'Localization/Argentina',
    'depends': [
        'partner_identification',
        # this is for demo data, for fiscal position data on account
        # and also beacuse it is essential for argentinian use
        'l10n_ar_states',
    ],
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Títulos de Personería y Tipos de documentos Arentinos',
    'data': [
        'data/res_partner_title_data.xml',
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
    'version': '9.0.1.0.0',
    'post_init_hook': 'post_init_hook',
}
