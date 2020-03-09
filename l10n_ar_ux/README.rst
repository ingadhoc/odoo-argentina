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

This module extends the l10n_ar module to add some usability improvesment:

#. Change USD symbol to "USD" instead of "$". This to avoid confusion when using multi company environment with ARS and USD at the same time.
#. Change postion of EUR symbol, Put it before the amounts in order to match to the ARS and USD currencies format,
#. Add portal support for AFIP responsability, and Identification type fields.
#. Show Currency Rate preview on invoice before posting.
#. Show final Currency Rate on invoice when already posted.
#. Add account tag data for Argentina (include jurisdiccion ones)
#. Add tax groups for withholding
#. Show Name fantasy in the partner form view.
#. Make some fields in company required if company is Argentina: vat, state_id, country_id, city, street, zip.
#. Set Non Monetary tag to accounts depending of the account type
#. Show Gross Income Jurisdiction in both partner and company
#. Add checks account link to chart template

Installation
============

To install this module, you need to:

#. Nothing to do

Configuration
=============

To configure this module, you need to:

#. Nothing to do

Usage
=====

To use this module, you need to:

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/odoo-argentina/issues>`_. In case of trouble, please
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
