import os

from django.contrib.sites.models import Site
from django.test import TestCase, tag
from django.test.utils import override_settings
from edc_registration.models import RegisteredSubject
from edc_sites.utils import add_or_update_django_sites
from random import shuffle
from tempfile import mkdtemp

from ..constants import ACTIVE
from ..models import RandomizationList
from ..randomization_list_importer import (
    RandomizationListImporter,
    RandomizationListImportError,
)
from ..randomization_list_verifier import (
    RandomizationListVerifier,
    RandomizationListError,
)
from ..randomizer import RandomizationError, AllocationError, InvalidAssignment
from ..randomizer import Randomizer, AlreadyRandomized
from ..site_randomizers import site_randomizers
from .make_test_list import make_test_list
from .models import SubjectConsent


my_sites = (
    (10, "site_one", "One"),
    (20, "site_two", "Two"),
    (30, "site_three", "Three"),
    (40, "site_four", "Four"),
    (50, "site_five", "Five"),
)


class TestRandomizer(TestCase):

    import_randomization_list = False
    site_names = [x[1] for x in my_sites]

    def setUp(self):
        super().setUp()
        add_or_update_django_sites(sites=my_sites)

    def populate_list(self, site_names=None, per_site=None, randomizers=None):
        randomizers = randomizers or site_randomizers.registry.values()

        for randomizer in randomizers:
            make_test_list(
                full_path=randomizer.get_randomization_list_path(),
                site_names=site_names or self.site_names,
                per_site=per_site,
            )
        RandomizationListImporter(randomizers=randomizers, overwrite=True)

    @override_settings(SITE_ID=40)
    def test_with_consent_insufficient_data(self):
        RandomizationListImporter(randomizers=[Randomizer])
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", user_created="erikvw"
        )
        self.assertRaises(
            RandomizationError,
            Randomizer,
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=None,
        )

    @override_settings(SITE_ID=40)
    def test_with_consent(self):
        RandomizationListImporter(randomizers=[Randomizer])
        site = Site.objects.get_current()
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", site=site, user_created="erikvw"
        )
        try:
            Randomizer(
                subject_identifier=subject_consent.subject_identifier,
                report_datetime=subject_consent.consent_datetime,
                site=subject_consent.site,
                user=subject_consent.user_created,
            )
        except Exception as e:
            self.fail(f"Exception unexpectedly raised. Got {str(e)}.")

    @override_settings(SITE_ID=40)
    def test_with_list_selects_first(self):
        self.populate_list()
        site = Site.objects.get_current()
        RandomizationList.objects.update(site_name=site.name)
        first_obj = RandomizationList.objects.all().first()
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", user_created="erikvw"
        )
        rando = Randomizer(
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_created,
        )
        self.assertEqual(rando.sid, first_obj.sid)

    @override_settings(SITE_ID=40)
    def test_updates_registered_subject(self):
        self.populate_list()
        site = Site.objects.get_current()
        RandomizationList.objects.update(site_name=site.name)
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", user_created="erikvw"
        )
        Randomizer(
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_created,
        )
        first_obj = RandomizationList.objects.all().first()
        rs = RegisteredSubject.objects.get(subject_identifier="12345")
        self.assertEqual(rs.subject_identifier, first_obj.subject_identifier)
        self.assertEqual(rs.sid, str(first_obj.sid))
        self.assertEqual(rs.randomization_datetime, first_obj.allocated_datetime)

    @override_settings(SITE_ID=40)
    def test_updates_list_obj_as_allocated(self):
        self.populate_list()
        site = Site.objects.get_current()
        RandomizationList.objects.update(site_name=site.name)
        RandomizationList.objects.all().first()
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", user_created="erikvw"
        )
        Randomizer(
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_created,
        )
        first_obj = RandomizationList.objects.all().first()
        self.assertEqual(first_obj.subject_identifier, "12345")
        self.assertTrue(first_obj.allocated)
        self.assertIsNotNone(first_obj.allocated_user)
        self.assertEqual(first_obj.allocated_user, subject_consent.user_created)
        self.assertEqual(first_obj.allocated_datetime, subject_consent.consent_datetime)
        self.assertGreater(first_obj.modified, subject_consent.created)

    @override_settings(SITE_ID=40)
    def test_cannot_rerandomize(self):
        self.populate_list()
        site = Site.objects.get_current()
        RandomizationList.objects.update(site_name=site.name)
        first_obj = RandomizationList.objects.all().first()
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", user_created="erikvw"
        )
        rando = Randomizer(
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_created,
        )
        self.assertEqual(rando.sid, first_obj.sid)
        self.assertRaises(
            AlreadyRandomized,
            Randomizer,
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_created,
        )

    @override_settings(SITE_ID=40)
    def test_error_condition1(self):
        """Assert raises if RegisteredSubject not updated correctly.
        """
        self.populate_list()
        site = Site.objects.get_current()
        RandomizationList.objects.update(site_name=site.name)
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", user_created="erikvw"
        )
        rando = Randomizer(
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_created,
        )
        rando.registered_subject.sid = None
        rando.registered_subject.save()
        with self.assertRaises(AlreadyRandomized) as cm:
            Randomizer(
                subject_identifier=subject_consent.subject_identifier,
                report_datetime=subject_consent.consent_datetime,
                site=subject_consent.site,
                user=subject_consent.user_created,
            )
        self.assertEqual(cm.exception.code, "edc_randomization.randomizationlist")

    @override_settings(SITE_ID=40)
    def test_error_condition2(self):
        """Assert raises if RandomizationList not updated correctly.
        """
        self.populate_list()
        site = Site.objects.get_current()
        RandomizationList.objects.update(site_name=site.name)
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", user_created="erikvw"
        )
        rando = Randomizer(
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_created,
        )
        rando.registered_subject.sid = None
        rando.registered_subject.save()
        with self.assertRaises(AlreadyRandomized) as cm:
            Randomizer(
                subject_identifier=subject_consent.subject_identifier,
                report_datetime=subject_consent.consent_datetime,
                site=subject_consent.site,
                user=subject_consent.user_created,
            )
        self.assertEqual(cm.exception.code, "edc_randomization.randomizationlist")

    def test_error_condition3(self):
        """Assert raises if RandomizationList not updated correctly.
        """
        self.populate_list()
        site = Site.objects.get_current()
        RandomizationList.objects.update(site_name=site.name)
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", site=site, user_created="erikvw"
        )
        Randomizer(
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_created,
        )
        RandomizationList.objects.update(subject_identifier=None)
        with self.assertRaises(AlreadyRandomized) as cm:
            Randomizer(
                subject_identifier=subject_consent.subject_identifier,
                report_datetime=subject_consent.consent_datetime,
                site=subject_consent.site,
                user=subject_consent.user_created,
            )
        self.assertEqual(cm.exception.code, "edc_registration.registeredsubject")

    def test_subject_does_not_exist(self):
        self.populate_list()
        site = Site.objects.get_current()
        RandomizationList.objects.update(site_name=site.name)
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", site=site, user_created="erikvw"
        )
        RegisteredSubject.objects.all().delete()
        self.assertRaises(
            RandomizationError,
            Randomizer,
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_modified,
        )

    def test_str(self):
        self.populate_list()
        site = Site.objects.get_current()
        RandomizationList.objects.update(site_name=site.name)
        subject_consent = SubjectConsent.objects.create(
            subject_identifier="12345", site=site, user_created="erikvw"
        )
        Randomizer(
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_created,
        )
        obj = RandomizationList.objects.all().first()
        self.assertTrue(str(obj))

    @override_settings(SITE_ID=40)
    def test_for_sites(self):
        """Assert that allocates by site correctly.
        """

        tmpdir = mkdtemp()

        class MyRandomizer(Randomizer):
            @classmethod
            def get_randomization_list_path(cls):
                return os.path.join(tmpdir, cls.randomization_list_filename)

        RandomizationList.objects.all().delete()
        self.populate_list(
            randomizers=[MyRandomizer], site_names=self.site_names, per_site=5
        )
        site_names = [obj.site_name for obj in RandomizationList.objects.all()]
        shuffle(site_names)
        self.assertEqual(len(site_names), len(self.site_names * 5))
        # consent and randomize 5 for each site
        for index, site_name in enumerate(site_names):
            site = Site.objects.get(name=site_name)
            subject_consent = SubjectConsent.objects.create(
                subject_identifier=f"12345{index}", site=site, user_created="erikvw"
            )
            MyRandomizer(
                subject_identifier=subject_consent.subject_identifier,
                report_datetime=subject_consent.consent_datetime,
                site=subject_consent.site,
                user=subject_consent.user_created,
            )
        # assert consented subjects were allocated SIDs in the
        # correct order per site.
        for site_name in site_names:
            randomized_subjects = [
                (obj.subject_identifier, str(obj.sid))
                for obj in RandomizationList.objects.filter(
                    allocated_site__name=site_name, subject_identifier__isnull=False
                ).order_by("sid")
            ]
            for index, obj in enumerate(
                SubjectConsent.objects.filter(site__name=site_name).order_by(
                    "consent_datetime"
                )
            ):
                rs = RegisteredSubject.objects.get(
                    subject_identifier=obj.subject_identifier
                )
                self.assertEqual(obj.subject_identifier, randomized_subjects[index][0])
                self.assertEqual(rs.sid, randomized_subjects[index][1])

        # clear out any unallocated
        RandomizationList.objects.filter(subject_identifier__isnull=True).delete()

        # assert raises on next attempt to randomize
        subject_consent = SubjectConsent.objects.create(
            subject_identifier=f"ABCDEF", site=site, user_created="erikvw"
        )
        self.assertRaises(
            AllocationError,
            Randomizer,
            subject_identifier=subject_consent.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
            site=subject_consent.site,
            user=subject_consent.user_modified,
        )

    @override_settings(SITE_ID=40)
    def test_not_loaded(self):
        try:
            RandomizationListVerifier(randomizer=Randomizer)
        except RandomizationListError as e:
            self.assertIn("Randomization list has not been loaded", str(e))
        else:
            self.fail("RandomizationListError unexpectedly NOT raised")

    @override_settings(SITE_ID=40)
    def test_cannot_overwrite(self):
        tmpdir = mkdtemp()

        class MyRandomizer(Randomizer):
            @classmethod
            def get_randomization_list_path(cls):
                return os.path.join(tmpdir, cls.randomization_list_filename)

        make_test_list(
            full_path=MyRandomizer.get_randomization_list_path(),
            site_names=self.site_names,
            count=5,
        )

        RandomizationListImporter(randomizers=[MyRandomizer])

        self.assertRaises(RandomizationListImportError, RandomizationListImporter)

    @override_settings(SITE_ID=40)
    def test_can_overwrite_explicit(self):
        tmpdir = mkdtemp()

        class MyRandomizer(Randomizer):
            @classmethod
            def get_randomization_list_path(cls):
                return os.path.join(tmpdir, cls.randomization_list_filename)

        make_test_list(
            full_path=MyRandomizer.get_randomization_list_path(),
            site_names=self.site_names,
            count=5,
        )

        RandomizationListImporter(randomizers=[MyRandomizer])

        try:
            RandomizationListImporter(overwrite=True)
        except RandomizationListImportError:
            self.fail("RandomizationListImportError unexpectedly raised")

    @override_settings(SITE_ID=40)
    def test_invalid_assignment(self):
        tmpdir = mkdtemp()

        class MyRandomizer(Randomizer):
            @classmethod
            def get_randomization_list_path(cls):
                return os.path.join(tmpdir, cls.randomization_list_filename)

        MyRandomizer.get_randomization_list_path()
        make_test_list(
            full_path=MyRandomizer.get_randomization_list_path(),
            site_names=self.site_names,
            # change to a different assignments
            assignments=[100, 101],
            count=5,
        )
        self.assertRaises(
            InvalidAssignment, RandomizationListImporter, randomizers=[MyRandomizer]
        )

    @override_settings(SITE_ID=40)
    def test_invalid_sid(self):
        # change to a different starting SID
        RandomizationListImporter()
        obj = RandomizationList.objects.all().order_by("sid").first()
        obj.sid = 100
        obj.save()
        with self.assertRaises(RandomizationListError) as cm:
            RandomizationListVerifier(randomizer=Randomizer)
        self.assertIn("Randomization list is invalid", str(cm.exception))

    @override_settings(SITE_ID=40)
    def test_invalid_count(self):
        site = Site.objects.get_current()
        # change number of SIDs in DB
        RandomizationListImporter()
        RandomizationList.objects.create(
            sid=100, assignment=ACTIVE, site_name=site.name
        )
        self.assertEqual(RandomizationList.objects.all().count(), 51)
        with self.assertRaises(RandomizationListError) as cm:
            RandomizationListVerifier(randomizer=Randomizer).message
        self.assertIn("Randomization list count is off", str(cm.exception))