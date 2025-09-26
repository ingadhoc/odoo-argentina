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
    "name": "Automatic Argentinian Withholdings on Payments",
    "version": "18.0.1.20.0",
    "author": "ADHOC SA,Odoo Community Association (OCA)",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "category": "Accounting & Finance",
    "data": [
        "security/ir.model.access.csv",
        "views/report_withholding_certificate_templates.xml",
        "views/account_payment_view.xml",
        "views/res_company_jurisdiction_padron_view.xml",
        "views/res_partner_view.xml",
        "views/account_tax_view.xml",
        "views/account_move_views.xml",
        "views/report_payment_receipt_templates.xml",
        "views/l10n_ar_payment_withholding_views.xml",
        "views/account_fiscal_position_view.xml",
        "wizard/account_payment_register_views.xml",
        "wizard/res_config_settings_views.xml",
    ],
    "demo": [
        "demo/ir_parameter.xml",
        "demo/account_fiscal_position_demo.xml",
        "demo/account_tax_demo.xml",
        "demo/res_partner_demo.xml",
        "demo/account_move_demo.xml",
    ],
    "depends": [
        "l10n_ar",
        "l10n_ar_ux",
        "l10n_ar_withholding",
        "account_payment_pro",
        "l10n_latam_check_ux",  # para reporte de pagos/recibos
    ],
    "external_dependencies": {
        "python": ["pyafipws"],
    },
    "installable": True,
    "auto_install": ["l10n_ar"],
    "post_load": "monkey_patch_synchronize_to_moves",
    "post_init_hook": "_l10n_ar_update_taxes",
}
