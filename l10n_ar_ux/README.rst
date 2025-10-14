.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========================
Argentinian Accounting UX
=========================

This module extends the l10n_ar module to add usability improvements and user experience enhancements specifically designed for Argentinian accounting practices.

**Table of contents**

.. contents::
   :local:

Features
========

Currency & Multi-Company Enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **USD Symbol Enhancement**: Changes USD symbol from "$" to "USD" to avoid confusion in multi-company environments using both ARS and USD currencies
* **EUR Symbol Position**: Repositions EUR symbol before amounts to match ARS and USD currency formats
* **Currency Rate Display**: Shows currency rate preview on invoices before posting and final rate after posting

Tax & VAT Management
~~~~~~~~~~~~~~~~~~~~

* **Default Tax Inclusion**: Sets taxes as included by default (useful for e-commerce)
* **VAT Discrimination Option**: Adds option to discriminate or not VAT taxes on journals without documents
* **Tax Groups for Withholding**: Includes specialized tax groups for Argentinian withholding taxes
* **Account Tags**: Comprehensive account tag data for Argentina including jurisdictional ones

Partner & AFIP Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

* **CUIT Display**: Shows CUIT when using checks or bank transfers for easy reference during bank transactions
* **Gross Income Jurisdiction**: Displays gross income jurisdiction information on partner records

Account Management
~~~~~~~~~~~~~~~~~~

* **Non-Monetary Tags**: Automatically sets non-monetary tags to accounts based on account type
* **Check Payment Enhancement**: Sends due dates to journal items for check payments

Reporting & Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~

* **Invoice Reports**: Implements "duplicado/triplicado" functionality on invoices (extends to delivery slips with l10n_ar_stock)
* **Transfer Reports**: Enhanced account transfer reports with Argentinian formatting

Installation
============

This module has **auto_install** enabled, which means it will be automatically installed when its dependencies are met:

* ``l10n_ar`` - Argentinian Localization
* ``account_internal_transfer`` - Internal Transfer functionality

To manually install this module:

#. Go to Apps menu
#. Search for "Argentinian Accounting UX"
#. Click Install

Configuration
=============

Journal Configuration
~~~~~~~~~~~~~~~~~~~~~

#. Go to **Accounting ‣ Configuration ‣ Journals**
#. For journals without documents, you can now configure VAT tax discrimination options
#. The VAT discrimination setting will be available in the journal configuration form

Company Configuration
~~~~~~~~~~~~~~~~~~~~~

#. Go to **Settings ‣ Companies ‣ Update Info**
#. Currency symbols and positions are automatically configured for Argentinian companies
#. Tax inclusion defaults are automatically set for e-commerce scenarios

Usage
=====

Currency Rate Management
~~~~~~~~~~~~~~~~~~~~~~~~

When creating invoices with foreign currencies:

#. Create a new invoice
#. Select a foreign currency (USD/EUR)
#. Before posting: A currency rate preview will be displayed
#. After posting: The final currency rate will be shown on the invoice

Check and Bank Transfer Payments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When processing payments:

#. Go to **Accounting ‣ Vendors ‣ Payments** or **Accounting ‣ Customers ‣ Payments**
#. Create a new payment using checks or bank transfers
#. Partner's CUIT will be automatically displayed for easy reference during bank transactions
#. Due dates are automatically sent to journal items for check payments

VAT Tax Discrimination
~~~~~~~~~~~~~~~~~~~~~~

For journals without electronic documents:

#. Go to journal configuration
#. Enable/disable VAT tax discrimination as needed
#. This affects how taxes are displayed and calculated on documents

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/odoo-argentina/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Authors
~~~~~~~

* ADHOC SA

Contributors
~~~~~~~~~~~~

* ADHOC SA <info@adhoc.com.ar>

Other credits
~~~~~~~~~~~~~

* This module integrates seamlessly with other Argentinian localization modules
* Special thanks to the Argentinian Odoo community for feedback and testing

Maintainer
~~~~~~~~~~

.. |maintainer-adhoc| image:: https://github.com/adhoc-dev.png?size=40px
    :target: https://github.com/adhoc-dev
    :alt: adhoc-dev

This module is maintained by |maintainer-adhoc|.

|company_logo|

This module is maintained by |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
