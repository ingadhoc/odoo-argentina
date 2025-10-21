.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==========================
Argentinian Purchase Stock
==========================

This module enhances Argentinian purchase order and quotation reports by integrating stock and warehouse information.

**Key Features:**

* Adds Incoterm information to purchase documents
* Displays warehouse shipping address when applicable
* Integrates with Argentinian purchase localization (`l10n_ar_purchase`)
* Automatically shows warehouse details for non-dropshipping orders

**Enhanced Report Information:**

When printing purchase orders or quotations, the following information is automatically added to the supplier section:

#. **Incoterm Code**: Displays the selected incoterm for international trade terms
#. **Shipping Address**: Shows warehouse name and address when:

   * No dropshipping address is configured (`dest_address_id` is not set)
   * The purchase order has a picking type with an associated warehouse

Installation
============

To install this module, you need to:

#. Have the `purchase_stock` and `l10n_ar_purchase` modules installed
#. The module will be automatically installed when both dependencies are present (auto_install=True)

Configuration
=============

No additional configuration is required. The module works automatically once installed.

**Optional Configuration:**

* **Incoterms**: Configure incoterms in **Settings > Configuration > Incoterms** if you need specific international trade terms
* **Warehouses**: Ensure your warehouses have proper addresses configured in **Inventory > Configuration > Warehouses**

Usage
=====

The module enhances purchase reports automatically:

#. **Creating Purchase Orders:**

   * Go to **Purchase > Orders > Purchase Orders**
   * Create or edit a purchase order
   * Select an **Incoterm** if applicable
   * Choose a **Deliver To** location (picking type with warehouse)

#. **Printing Reports:**

   * Print the purchase order or quotation
   * The report will automatically include:

     * Incoterm code (if configured)
     * Warehouse shipping address (if no dropshipping address is set)

#. **Report Enhancement Details:**

   * **Incoterm Display**: Shows the incoterm code in the supplier information section
   * **Warehouse Address**: Displays warehouse name and full address when conditions are met
   * **Conditional Logic**: Only shows warehouse address when no specific dropshipping address is configured

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
