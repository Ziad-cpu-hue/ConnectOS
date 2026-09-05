from django.test import TestCase
from django.urls import reverse

from core.models import Company, User
from nas_manager.models import NASServer
from radius_core.models import RadNas


class NasRadiusSyncTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="شركة تجربة")

    def test_saving_nas_creates_radnas_row(self):
        nas = NASServer.objects.create(
            company=self.company, name="جهاز 1", ip_address="10.0.0.1", secret="mysecret",
        )
        row = RadNas.objects.get(nasname="10.0.0.1")
        self.assertEqual(row.secret, "mysecret")

    def test_deleting_nas_removes_radnas_row(self):
        nas = NASServer.objects.create(
            company=self.company, name="جهاز 2", ip_address="10.0.0.2", secret="s2",
        )
        nas.delete()
        self.assertFalse(RadNas.objects.filter(nasname="10.0.0.2").exists())


class MandatoryContentFilterTests(TestCase):
    """يتأكد إن سكريبت التركيب دايمًا بيحتوي على الحجب الإجباري للمحتوى
    الإباحي — بدون أي شرط أو إعداد ممكن يمنع لزقه. لو حد غيّر الكود بعدين
    وحاول يخلي الفقرة دي اختيارية، الاختبار ده لازم يفشل وينبّه."""

    def setUp(self):
        self.company = Company.objects.create(name="شركة الفلترة")
        self.owner = User.objects.create_user(
            username="owner_filter", password="pass12345", company=self.company, role="owner",
        )
        self.nas = NASServer.objects.create(
            company=self.company, name="جهاز الفلترة", ip_address="10.0.0.9", secret="s",
        )

    def test_setup_script_always_contains_mandatory_content_filter(self):
        self.client.login(username="owner_filter", password="pass12345")
        resp = self.client.get(reverse("nas_manager:setup_script", args=[self.nas.pk]))
        self.assertContains(resp, "ip dns adlist")
        self.assertContains(resp, "ConnectOS-mandatory-adult-content-filter")
        self.assertContains(resp, "dst-port=53")

    def test_setup_script_always_contains_fair_share_queue_definition(self):
        self.client.login(username="owner_filter", password="pass12345")
        resp = self.client.get(reverse("nas_manager:setup_script", args=[self.nas.pk]))
        self.assertContains(resp, "connectos-fair-share")
        self.assertContains(resp, "pcq")
