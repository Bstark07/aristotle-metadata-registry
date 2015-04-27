Extending Aristotle-MDR
=======================

One of the core features of the ISO/IEC 11179-3 information model is the ability
to extend the models by subclassing from the included items. The core item that
most 11179 objects are based on is the "Concept".

Due to this encouragement of inheritance and enhancement, Aristotle-MDR follows
similar principles and uses the Object-Oriented approach of
`Python <https://www.python.org/>`_ and `Django <https://www.djangoproject.com/>`_,
to expose a rich API that makes adding new content, and altering templates quick and easy.

Before starting it is strongly encouraged that you have a clear understanding of
the `Python programming language <https://www.python.org/about/gettingstarted/>`_ as well as
`how to build Django apps and sites <https://docs.djangoproject.com/en/dev/intro/tutorial01/>`_.

.. toctree::
   :maxdepth: 2

   new_content_type.rst
   registering_new_content_types.rst
   modelling_weak_relationships.rst
   downloads.rst
   templates.rst
   including_extra_content.rst
   out_of_the_box_features.rst
   templatetags.rst
   using_permissions.rst
   using_concept_manager.rst
