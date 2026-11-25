##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
##############################################################################
{
    "name": "Thermal Invoice Ticket - Argentinian Localization",
    "version": "20.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Argentinian fiscal blocks on the 80mm thermal ticket",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "depends": [
        "account_thermal_ticket",
        "l10n_ar_edi",
        # `res.partner.start_date` (activities start date printed on the
        # fiscal header) is added by this module, not by the localization.
        "l10n_ar_ux",
    ],
    "data": [
        "views/thermal_invoice_reports.xml",
        "views/thermal_invoice_templates.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "l10n_ar_thermal_ticket/static/src/scss/thermal_invoice_ar.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
