.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===============================================
CBU Addition to Banks and Argentine Bank List
===============================================

* Complete list of financial entities authorized by the BCRA in the Argentine Republic.
* Includes contact information, addresses, and BIC/SWIFT codes of banks.
* Compatible with Argentine localization (l10n_ar) to facilitate banking operations.

Main Features
=============

* **83+ preloaded Argentine banks**: Includes both national and international banks operating in Argentina
* **Information**: Name, BIC/SWIFT code, address, phone, email, city and province
* **BCRA codes**: Uses official codes from the Central Bank of the Argentine Republic


Installation
============

#. This module is automatically installed when l10n_ar is installed (auto_install: True)
#. If you need to install it manually: go to Apps > search "l10n_ar_bank" > Install

Configuration
=============

#. No additional configuration required
#. Banks are automatically loaded when installing the module
#. Data is immediately available in Accounting > Configuration > Banks

Usage
=====

To use this module, you can:

#. **Configure company bank accounts**: Go to Contacts > Configuration > Bank Accounts and create a new account by selecting the desired bank from the list
#. **Create contacts with banking information**: In contacts (customers/suppliers), you can select banks from the preloaded list
#. **Invoicing**: Banking data is automatically used in reports and invoices
#. **Transfers**: Facilitates the configuration of bank transfers with correct data
