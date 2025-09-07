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
    "name": "Withholdings Python Formula",
    "summary": "Allow to use Python Formula in Argentinian Fiscal Positions",
    "version": "18.0.1.0.0",
    "author": "ADHOC SA,Odoo Community Association (OCA)",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "category": "Accounting & Finance",
    "data": ["views/account_fiscal_position_view.xml"],
    "demo": [
        "demo/account_fiscal_position_demo.xml",
        "demo/res_partner_demo.xml",
    ],
    "depends": [
        "l10n_ar_tax",
    ],
    "installable": True,
    "auto_install": False,
}
