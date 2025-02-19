====
DAS2
====

.. 
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! This file is generated by oca-gen-addon-readme !!
   !! changes will be overwritten.                   !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! source digest: sha256:35b6b31fa7026a1912266d10fd5ae17f08017d0245f3a7553853e78f25352106
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-OCA%2Fl10n--france-lightgray.png?logo=github
    :target: https://github.com/OCA/l10n-france/tree/14.0/l10n_fr_das2
    :alt: OCA/l10n-france
.. |badge4| image:: https://img.shields.io/badge/weblate-Translate%20me-F47D42.png
    :target: https://translation.odoo-community.org/projects/l10n-france-14-0/l10n-france-14-0-l10n_fr_das2
    :alt: Translate me on Weblate
.. |badge5| image:: https://img.shields.io/badge/runboat-Try%20me-875A7B.png
    :target: https://runboat.odoo-community.org/builds?repo=OCA/l10n-france&target_branch=14.0
    :alt: Try me on Runboat

|badge1| |badge2| |badge3| |badge4| |badge5|

This module adds support for `DAS2 <https://www.impots.gouv.fr/portail/formulaire/das2/etat-des-honoraires-vacations-commissions-courtages-ristournes-et-jetons>_`, which is an annual fiscal declaration also called *Déclaration d'honoraires*. It will allow you to auto-generate the lines of DAS2 from the accounting entries, check the result, manually update lines if needed and eventually generate a declaration file. Then send the declaration file to the French tax office via your professional account on *impots.gouv.fr*

The specifications of the file are available on `this page <https://www.impots.gouv.fr/les-cahiers-des-charges-tdbilateral>`_.

**Table of contents**

.. contents::
   :local:

Installation
============

This module requires the Python lib `pyfrdas2 <https://pypi.org/project/pyfrdas2/>`_. As this lib contains the PGP encryption keys of the DGFiP used to encrypt the declaration file and as these keys are changed every year, check that the lib is up-to-date before using the module for a new year.

To install this lib, run:

.. code::

  pip3 install --upgrade pyfrdas2

Configuration
=============

On the supplier form view, in the *Accounting* tab, you will see a section *DAS2*. For the suppliers that must be declared in DAS2, you must set:

* the DAS2 Type,
* the job for the DAS2 declaration,
* their SIRET number (for French suppliers only),
* their full address (street, zip code, city and country).

On the company configuration form, the APE code, SIRET and address must be set.

For the user responsible for the declaration, the phone number and email must be set on his related partner form (name, email and phone number are used in the DAS2 declaration file).

If you want to encrypt the declaration file with the DGFiP's **test** PGP key, ensure that your Odoo server configuration file has the following parameter:

.. code::

  running_env = test

Otherwise, Odoo will use DGFiP's **production** PGP key.

Usage
=====

Go to the menu *Accounting > Reports > French Statements > DAS2* and create a new DAS2 report.

Then click on the button *Generate Lines*. Check and edit the generated lines. You can get the details of the computation performed by Odoo in the *Note* fields of each line.

You may have a yellow warning banner that warn you about suppliers that have expenses recorded in accounts such as 622100 Commissions et courtages sur achats, 622200 Commissions et courtages sur ventes, 622600 Honoraires, 622800 Rémunérations d'intermédiaires divers, 653000 Jetons de présence, 651600 Droits d'auteur et de reproduction that are not configured for DAS2.

Once your declaration is OK, click on the button *Done*: it will generate the DAS2 file and set the declaration to *Done* state (all the fields become readonly).

To send the file to the French tax office, go to your professional account on `impots.gouv.fr <https://www.impots.gouv.fr/>`_, go to the menu **Déclarer > Tiers déclarant** and then click on the button **Déposer un fichier**. Select **Salaires et/ou honoraires** and follow the instructions.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/l10n-france/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us to smash it by providing a detailed and welcomed
`feedback <https://github.com/OCA/l10n-france/issues/new?body=module:%20l10n_fr_das2%0Aversion:%2014.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* Akretion

Contributors
~~~~~~~~~~~~

* Alexis de Lattre <alexis.delattre@akretion.com>

Maintainers
~~~~~~~~~~~

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

.. |maintainer-alexis-via| image:: https://github.com/alexis-via.png?size=40px
    :target: https://github.com/alexis-via
    :alt: alexis-via

Current `maintainer <https://odoo-community.org/page/maintainer-role>`__:

|maintainer-alexis-via| 

This module is part of the `OCA/l10n-france <https://github.com/OCA/l10n-france/tree/14.0/l10n_fr_das2>`_ project on GitHub.

You are welcome to contribute. To learn how please visit https://odoo-community.org/page/Contribute.
