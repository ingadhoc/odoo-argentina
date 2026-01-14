==================================================
Automatic Argentinian Withholdings on Payments
==================================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-ingadhoc%2Fodoo--argentina-lightgray.png?logo=github
    :target: https://github.com/ingadhoc/odoo-argentina/tree/19.0/l10n_ar_tax
    :alt: ingadhoc/odoo-argentina

|badge1| |badge2| |badge3|

This module implements automatic calculation of Argentine withholdings and perceptions based on fiscal positions and tax configurations.

**Table of contents**

.. contents::
   :local:

Features
========

* Automatic withholding calculation based on jurisdictions and tax tables
* Support for perception taxes
* Integration with Argentine tax identification types (CUIT, CUIL, DNI)
* Configurable tax ratios for specific jurisdictions (e.g., Córdoba)
* Fiscal position-based tax automation
* Withholding certificates generation
* Integration with ARCA webservices

Configuration
=============

After installation:

1. Go to **Accounting > Configuration > Taxes** to configure withholding and perception taxes
2. Set up fiscal positions in **Accounting > Configuration > Fiscal Positions**
3. Configure partner tax identification in **Contacts** (CUIT/CUIL/DNI)
4. Configure tax ratios in the tax configuration. The ratio must be an integer between 1 and 100 and represents the percentage of the taxable base to consider when applying the tax. The ratio is only used when the tax's computation method is percentage-based. Although this ratio can be used for any tax, it was requested only for Córdoba jurisdiction.


Usage
=====

* Withholdings are automatically calculated when creating payments based on the partner's fiscal position
* Perception taxes are applied based on the configured fiscal positions
* Withholding certificates can be generated from the payment form
* Tax calculations respect jurisdiction-specific rules and rates


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/ingadhoc/odoo-argentina/issues>`_.
In case of trouble, please check there if your issue has already been reported.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* ADHOC SA

Contributors
~~~~~~~~~~~~

* ADHOC SA

Maintainers
~~~~~~~~~~~

This module is maintained by ADHOC SA.

.. image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

To contribute to this module, please visit https://www.adhoc.com.ar.
