=====
Aristotle MetaData Registry (Aristotle-MDR)
=====

|build-status| |docs| |coveralls| |codecov|

Aristotle-MDR is an open-source metadata registry as laid out by the requirements
of the ISO/IEC 11179:2013 specification.

Aristotle-MDR represents a new way to manage and federate content built on and extending
the principles of leading metadata registry. The code of Aristotle is completely open-source,
building on the Django web framework and the mature model of the 11179 standard,
agencies can easily run their own metadata registries while also having the ability
to extend the information model and tap into the permissions and roles of ISO 11179.

By allowing organisations to run their own independant registries the are able to
expose authoritative metadata and the governance processes behind its creation,
and building upon known and open systems agencies, can build upon a stable platform
or the sharing of 11179 metadata items.

Quick start
-----------

1. Add "aristotle_mdr" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        ...
        'haystack',
        'aristotle_mdr',
        'grappelli',
        ...
    )

   To ensure that search indexing works properly ``haystack`` **must** be installed before `aristotle_mdr`.
   If you want to take advantage of Aristotle's access-key shortcut improvements for the admin interface,
   make sure it is installed *before* ``grappelli``.

2. Include the Aristotle-MDR URLconf in your project ``urls.py``. Because Aristotle will
   form the majority of the interactions with the site, and the Aristotle includes a
   number of URLconfs for supporting apps its recommended to included it at the
   server root, like this::

    url(r'^/', include('aristotle_mdr.urls')),

3. Run ``python manage.py migrate`` to create the Aristotle-MDR Database.

4. (Optional) Compile the multilingual resource files for improved performance, like so::

     django-admin.py compilemessages

5. Start the development server and visit ``http://127.0.0.1:8000/``
   to see the home page.

For a complete example of how to successfully include Aristotle, see the `aristotle_mdr/tests/settings.py` settings file.

**A live aristotle instance is available on PythonAnywhere at:** ``http://aristotle.pythonanywhere.com/``.
Be aware, this is an active development instance and may go down from occasionally.

.. |build-status| image:: https://travis-ci.org/LegoStormtroopr/aristotle-metadata-registry.svg?branch=master
    :alt: build status
    :scale: 100%
    :target: https://travis-ci.org/LegoStormtroopr/aristotle-metadata-registry

.. |docs| image:: https://readthedocs.org/projects/aristotle-metadata-registry/badge/?version=latest
    :alt: Documentation Status
    :scale: 100%
    :target: https://readthedocs.org/projects/aristotle-metadata-registry/

.. |coveralls| image:: https://coveralls.io/repos/LegoStormtroopr/aristotle-metadata-registry/badge.png?branch=master
    :alt: Code coverage on coveralls
    :scale: 100%
    :target: https://coveralls.io/r/LegoStormtroopr/aristotle-metadata-registry?branch=master

.. |codecov| image:: https://codecov.io/github/LegoStormtroopr/aristotle-metadata-registry/coverage.svg?branch=master
    :alt: Code coverage on code cov (includes branch checks)
    :scale: 100%
    :target: https://codecov.io/github/LegoStormtroopr/aristotle-metadata-registry?branch=master
