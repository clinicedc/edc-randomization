import csv
import os

from edc_utils import get_utcnow
from tqdm import tqdm


class RandomizationListExporterError(Exception):
    pass


class RandomizationListExporter:
    def __init__(
        self,
        randomizer_cls=None,
        verbose=None,
        user=None,
    ):
        self.randomizer_cls = randomizer_cls
        self.verbose = True if verbose is None else verbose
        self.user = user

    # TODO: link to randomizer for model;
    # TODO: check user has permissions to export; create permissions at settings, like pharma?
    # TODO: confirm file path exists
    # TODO: accept custom file path
    def export(self):
        timestamp = get_utcnow().strftime("%Y%m%d%H%M")
        filename = os.path.expanduser(f"~/meta_rando_exported_{timestamp}.csv")
        fieldnames = [
            "subject_identifier",
            "sid",
            "assignment",
            "allocated_datetime",
            "site_name",
            "allocation",
        ]
        with open(filename, "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="|")
            writer.writeheader()
            total = (
                self.randomizer_cls.model_cls()
                .objects.filter(subject_identifier__isnull=False)
                .count()
            )
            for obj in tqdm(
                self.randomizer_cls.model_cls()
                .objects.filter(subject_identifier__isnull=False)
                .order_by("sid"),
                total=total,
            ):
                row = {fld: getattr(obj, fld) for fld in fieldnames}
                writer.writerow(row)
