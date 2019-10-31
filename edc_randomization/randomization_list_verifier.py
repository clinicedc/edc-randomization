import csv
import os
import sys

from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import OperationalError, ProgrammingError


class RandomizationListError(Exception):
    pass


class RandomizationListVerifier:

    """Verifies the RandomizationList upon instantiation.
    """

    default_fieldnames = ["sid", "assignment", "site_name"]

    def __init__(self, randomizer=None, fieldnames=None):
        self.messages = []

        self.randomizer = randomizer
        self.fieldnames = fieldnames or self.default_fieldnames
        try:
            self.count = self.randomizer.model_cls().objects.all().count()
        except (ProgrammingError, OperationalError) as e:
            self.messages.append(str(e))
        else:
            if self.count == 0:
                self.messages.append(
                    "Randomization list has not been loaded. "
                    "Run the 'import_randomization_list' management command "
                    "to load before using the system. "
                    "Resolve this issue before using the system."
                )

            else:
                if not os.path.exists(self.randomizer.get_randomization_list_path()):
                    self.messages.append(
                        f"Randomization list file does not exist but SIDs "
                        f"have been loaded. Expected file "
                        f"{self.randomization_list_path}. "
                        f"Resolve this issue before using the system."
                    )
                else:
                    message = self.verify_list()
                    if message:
                        self.messages.append(message)
        if self.messages:
            if (
                "migrate" not in sys.argv
                and "makemigrations" not in sys.argv
                and "import_randomization_list" not in sys.argv
            ):
                raise RandomizationListError(", ".join(self.messages))

    def verify_list(self):

        message = None

        with open(self.randomizer.get_randomization_list_path(), "r") as f:
            reader = csv.DictReader(f, fieldnames=self.fieldnames)
            for index, row in enumerate(reader):
                row = {k: v.strip() for k, v in row.items()}
                if index == 0:
                    continue
                message = self.inspect_row(index, row)
                if message:
                    break
        if not message:
            with open(self.randomizer.get_randomization_list_path(), "r") as f:
                reader = csv.DictReader(f, fieldnames=self.fieldnames)
                lines = sum(1 for row in reader)
            if self.count != lines - 1:
                message = (
                    f"Randomization list count is off. Expected {self.count}. "
                    f"Got {lines - 1}. See file "
                    f"{self.randomizer.get_randomization_list_path()}. "
                    f"Resolve this issue before using the system."
                )
        return message

    def inspect_row(self, index, row):
        message = None
        try:
            obj = self.randomizer.model_cls().objects.get(sid=row["sid"])
        except ObjectDoesNotExist:
            try:
                obj = self.randomizer.model_cls().objects.all()[index]
            except IndexError:
                pass
            else:
                message = (
                    f"Randomization list is invalid. List has invalid SIDs. "
                    f"File data does not match model data. See file "
                    f"{self.randomizer.get_randomization_list_path()}. "
                    f"Resolve this issue before using the system. "
                    f"Problem started on line {index + 1}. "
                    f'Got {row["sid"]} != {obj.sid}.'
                )
        else:
            assignment = self.randomizer.get_assignment(row)
            if obj.assignment != assignment or obj.site_name != row["site_name"]:
                message = (
                    f"Randomization list is invalid. File data "
                    f"does not match model data. See file "
                    f"{self.randomizer.get_randomization_list_path()}. "
                    f"Resolve this issue before using the system. "
                    f"Got {assignment} != '{obj.assignment}'."
                )
        return message
