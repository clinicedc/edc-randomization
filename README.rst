|pypi| |actions| |codecov| |downloads|


edc-randomization
=================

Randomization objects for clinicedc projects


Overview
++++++++

The default ``randomizer`` class will refer to and update the randomization list in the default ``RandomizationList`` model. You may refer to more than one ``randomizer`` within a project by declaring a custom ``randomizer`` class and registering it with ``site_randomizer``. Randomizers are referred to by name in ``site_randomizer``. Each ``randomizer`` class should have a custom model associated with it. See the ``RandomizationListModelMixin`` and its ``randomizer_cls`` attribute.


Importing from CSV
++++++++++++++++++
Use the ``randomizer`` class to import from your CSV file. The class has all the attributes required to find the file and know which model class
to populate.

..code-block:: python

    randomizer_cls = site_randomizers.get("default")
    randomizer_cls.import_list()

Customizing the default randomizer
++++++++++++++++++++++++++++++++++
The important values are:

* sid: unique sequence
* site: Site name
* allocation: integer representation of arms (e.g. 1, 2)

The default ``randomizer`` is loaded at startup, uses the ``RandomizationList`` model and an allocation map of "Active=1" vs "Placebo=2".

Creating a custom randomizer
++++++++++++++++++++++++++++

Unless you explicitly tell it not to, the ``site_randomizer`` will load the default ``randomizer``. This may be OK if you have multiple randomizers within the same protocol where the default is one of them. If not, you can prevent the "default" from loading by updating ``settings`` with::

    EDC_RANDOMIZATION_REGISTER_DEFAULT_RANDOMIZER=False

To create a custom ``randomizer`` class, declare a subclass of ``Randomizer`` in file ``randomizers.py`` at the root of your app. On startup the ``site_randomizer`` will pick it up. See the ``Randomizer`` class.

..code-block:: python
    
    # randomizers.py
    
    class MyRandomizer(Randomizer):
        name = "my_randomizer"
        model = "edc_randomization.myrandomizationlist"
        randomization_list_path = tmpdir
        assignment_map = {"Intervention": 1, "Control": 0}
        assignment_description_map = {"Intervention": "Fluconazole plus flucytosine", "Control": "Fluconazole"}


    class MyOtherRandomizer(Randomizer):
        name = "my_other_randomizer"
        model = "edc_randomization.myotherrandomizationlist"
        randomization_list_path = tmpdir


.. |pypi| image:: https://img.shields.io/pypi/v/edc-randomization.svg
    :target: https://pypi.python.org/pypi/edc-randomization

.. |actions| image:: https://github.com/clinicedc/edc-randomization/workflows/build/badge.svg?branch=develop
  :target: https://github.com/clinicedc/edc-randomization/actions?query=workflow:build

.. |codecov| image:: https://codecov.io/gh/clinicedc/edc-randomization/branch/develop/graph/badge.svg
  :target: https://codecov.io/gh/clinicedc/edc-randomization

.. |downloads| image:: https://pepy.tech/badge/edc-randomization
   :target: https://pepy.tech/project/edc-randomization
