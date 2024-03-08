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

Adapt purchase order report and quotation report to Argentinean localization. Replaces the native Odoo purchase report with a new one that has the same look and feel of the Argentinean electronic invoice.


When a request for quotation is printed in an argentinean company then the report will contain the argentinean localization header with this leyend: "Invalid document as invoice". Then the header also will contain the information of the company that generates de purchase order such as name, address, telephone number, website, order number, date, fiscal position, vat, iibb number, date of activities start.
Supplier data such as name, address, vat, vat cond, purchase representative, payment terms, order reference and shipping address are added below the header.
If a purchase order is printed, the format is the same as the request for quotation but the name of the report changes depending on the status of the purchase order.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Nothing to configure

Usage
=====

To use this module, you need to:

#. Go to ...

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
