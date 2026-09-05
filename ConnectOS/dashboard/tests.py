from django.test import TestCase
from django.urls import reverse

from core.models import Company, User


class PlatformOverviewSecurityTests(TestCase):
    """اختبار Regression للثغرة الأمنية اللي كانت موجودة (Broken Access
    Control على /dashboard/platform/). أي تعديل مستقبلي يكسر الحماية دي،
    الاختبار ده هيفشل فورًا."""

    def setUp(self):
        self.company = Company.objects.create(name="شركة أ")
        self.owner = User.objects.create_user(
            username="owner_test", password="pass12345", company=self.company, role="owner"
        )
        self.platform_admin = User.objects.create_user(
            username="admin_test", password="pass12345", role="platform_admin"
        )

    def test_owner_cannot_access_platform_overview(self):
        self.client.login(username="owner_test", password="pass12345")
        resp = self.client.get(reverse("dashboard:platform_overview"))
        self.assertEqual(resp.status_code, 403, "صاحب شبكة عادي لازم ياخد 403 مش يشوف بيانات كل الشركات")

    def test_platform_admin_can_access_platform_overview(self):
        self.client.login(username="admin_test", password="pass12345")
        resp = self.client.get(reverse("dashboard:platform_overview"))
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse("dashboard:platform_overview"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)
