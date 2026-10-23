.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

============================
Argentinean Purchase Report
============================

This module adapts the purchase order and quotation reports to comply with Argentinean localization standards. It replaces the native Odoo purchase reports with customized templates that match the format and design of Argentinean electronic invoices.

Features
========

Report Customization
--------------------

* **Custom Header**: Adapts purchase reports to use the Argentinean localization header layout
* **Document Identification**: Includes "Invalid document as invoice" legend for compliance
* **Company Information**: Displays comprehensive company data including:

  * Company name, address, telephone, and website
  * VAT number and AFIP responsibility type
  * IIBB (Gross Income Tax) number
  * Date of business activities start

* **Supplier Information**: Enhanced supplier section with:

  * Supplier name and commercial address
  * VAT condition and identification number
  * AFIP responsibility type
  * Purchase representative details

Report Types
------------

* **Request for Quotation**: Customized quotation report with Argentinean format
* **Purchase Order**: Adapted purchase order report that changes dynamically based on order status:

  * Draft/Sent/To Approve: "Request for Quotation"
  * Purchase/Done: "Purchase Order"
  * Cancelled: "Cancelled Purchase Order"

Tax Display
-----------

* **VAT Column**: Replaces generic "Taxes" column with "% VAT" column
* **Tax Filtering**: Shows only VAT taxes with AFIP codes
* **Tax Labels**: Displays proper tax names and invoice labels

Additional Features
-------------------

* **Payment Terms**: Displays payment terms information
* **Order References**: Shows supplier's order reference
* **Shipping Address**: Includes delivery address when specified
* **Approval Dates**: Shows approval date for confirmed orders
* **Page Numbering**: Professional footer with page numbers

Installation
============

To install this module, you need to:

#. Install the module from the Apps menu
#. No additional configuration is required

The module automatically activates when working with Argentinean companies (country code "AR").

Configuration
=============

No specific configuration is required. The module automatically:

* Detects Argentinean companies based on country code
* Applies the localized reports to purchase orders and quotations
* Uses the company's secondary color for styling elements

Usage
=====

Once installed, the module works automatically:

#. Create or edit a purchase order in an Argentinean company
#. Print the quotation or purchase order
#. The report will use the Argentinean localized format
#. All company and supplier information will be displayed according to local requirements

The reports include all necessary information for Argentinean business compliance and maintain professional formatting consistent with electronic invoice standards.

Known Issues / Roadmap
======================

* The module inherits templates with high priority (20) to ensure proper functionality
* Some fields from other modules (like incoterms from sale_stock) may not appear due to inheritance priorities

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/argentina-sale/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
