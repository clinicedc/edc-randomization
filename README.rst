edc-randomization
=================

Randomization objects for clinicedc projects


.. code-block:: python

    import csv
    import os

    from django.apps import apps as django_apps
    from edc_randomization import AllocationError
    from pprint import pprint


    def get_assignment(allocation):
        if allocation == 1:
            return 'control'
        elif allocation == 2:
            return 'single_dose'
        else:
            raise AllocationError(f'Invalid allocation. Got {allocation}')

    def import_additional(filename=None, model=None, dry_run=None):
        filename = filename or "~/rando_additional.txt"
        model = model or "ambition_rando.randomizationlist"
        randomizationlist_model_cls = django_apps.get_model(model)
        with open(os.path.join(os.path.expanduser(filename)), "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k: v.strip() for k, v in row.items()}
                try:
                    randomizationlist_model_cls.objects.get(sid=row["sid"])
                except ObjectDoesNotExist:
                    obj = RandomizationList(
                        id=uuid4(),
                        sid=row["sid"],
                        assignment=row['assignment'],
                        site_name=row['site'],
                        allocation=get_allocation(row['assignment']),
                    )
                    objs.append(obj)
        if dry_run:
            pprint(objs)
        else:
            randomizationlist_model_cls.objects.bulk_create(objs)