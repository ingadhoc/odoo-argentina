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
* **Bank catalog**: Adds the BCRA code to the Banks of base_bank, that can be searched by it
* **Bank accounts**: Choosing a bank fills the clearing number of the account with its BCRA code
* **BCRA Code label**: Clearing number label for Argentine bank accounts


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

#. **Manage banks**: Go to Accounting > Configuration > Banks to see, search by name or BCRA code, and edit the banks
#. **Configure bank accounts**: When creating a bank account, select the desired bank from the list; its name, BIC and BCRA code are filled in the account
#. **Create contacts with banking information**: In contacts (customers/suppliers), you can select banks from the preloaded list
#. **Invoicing**: Banking data is automatically used in reports and invoices
#. **Transfers**: Facilitates the configuration of bank transfers with correct data
