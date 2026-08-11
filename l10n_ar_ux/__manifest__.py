{
    "name": "Argentinian Accounting UX",
<<<<<<< 9320060b5713980ff23b3ba461dff58bdb23b3d0
    "version": "19.0.1.10.0",
||||||| fedd5383b76a725780743ca7606522531f2a9ff2
    "version": "18.0.1.13.0",
=======
    "version": "18.0.1.14.0",
>>>>>>> a9d2136bd2682608d7e40ed1dfced540c96d9686
    "category": "Localization/Argentina",
    "sequence": 14,
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "summary": "",
    "depends": [
        "l10n_ar",
        "account_internal_transfer",
    ],
    "data": [
        "data/res_currency_data.xml",
        "data/account_account_tag_data.xml",
        "views/res_partner_view.xml",
        "views/afip_concept_view.xml",
        "views/afip_tax_view.xml",
        "views/report_invoice.xml",
        "reports/report_account_transfer.xml",
        "views/account_payment_view.xml",
        "views/account_journal_views.xml",
        "views/ir_actions_views.xml",
        "views/res_config_settings_views.xml",
        "reports/account_invoice_report_view.xml",
        "security/ir.model.access.csv",
        "security/l10n_ar_ux_security.xml",
        "data/res_groups_data.xml",
        "views/account_fiscal_position_view.xml",
        "views/account_move_debit_note_view.xml",
    ],
    "demo": [
        "demo/res_partner_demo.xml",
        "demo/l10n_ar_ux_demo.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}
